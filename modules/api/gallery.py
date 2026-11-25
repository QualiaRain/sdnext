import io
import os
import time
import asyncio
import base64
from secrets import compare_digest
from urllib.parse import quote, unquote
from anyio import CapacityLimiter, to_thread
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketState
from pydantic import BaseModel, Field # pylint: disable=no-name-in-module
from PIL import Image
from modules import shared, images, files_cache, modelstats
from modules.logger import log
from modules.paths import resolve_output_path


debug = log.debug if os.environ.get('SD_BROWSER_DEBUG', None) is not None else lambda *args, **kwargs: None
OPTS_FOLDERS = [
    "outdir_samples",
    "outdir_txt2img_samples",
    "outdir_img2img_samples",
    "outdir_control_samples",
    "outdir_extras_samples",
    "outdir_save",
    "outdir_video",
    "outdir_init_images",
    "outdir_grids",
    "outdir_txt2img_grids",
    "outdir_img2img_grids",
    "outdir_control_grids",
]

### class definitions

class ReqFiles(BaseModel):
    folder: str = Field(title="Folder")

class ItemFolder(BaseModel):
    path: str = Field(title="Path", description="Folder path")
    label: str = Field(title="Label", description="Folder display label")

### ws connection manager

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        agent = ws._headers.get("user-agent", "") # pylint: disable=protected-access
        debug(f'Browser WS connect: client={ws.client.host} agent="{agent}"')
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        debug(f'Browser WS disconnect: client={ws.client.host}')
        self.active.remove(ws)

    async def send(self, ws: WebSocket, data: str | dict | bytes):
        # debug(f'Browser WS send: client={ws.client.host} data={type(data)}')
        if ws.client_state != WebSocketState.CONNECTED:
            return
        if isinstance(data, bytes):
            await ws.send_bytes(data)
        elif isinstance(data, dict):
            await ws.send_json(data)
        elif isinstance(data, str):
            await ws.send_text(data)
        else:
            debug(f'Browser WS send: client={ws.client.host} data={type(data)} unknown')

    async def broadcast(self, data: str | dict | bytes):
        for ws in self.active:
            await self.send(ws, data)

def listing_lines(folder: str, files):
    """Yield one 'folder##F##file' line per file as split by ui/gallery.ts; folder quoting and path root are computed once per listing."""
    prefix = quote(folder) + '##F##'
    prefix = prefix[:1] + ":" + prefix[4:] if prefix[1:4] == "%3A" else prefix
    root = os.path.join(os.path.abspath(folder), '')
    n = len(root)
    for f in files:
        file = f[n:] if f.startswith(root) else os.path.relpath(f, folder) # files_cache paths are normalized and below abspath(folder), where the slice equals relpath
        yield prefix + quote(file)

### api definitions

def register_api(api): # register api
    manager = ConnectionManager()

    def get_video_thumbnail(filepath):
        from modules.video import get_video_params
        try:
            stat_size, stat_mtime = modelstats.stat(filepath)
            frames, fps, duration, width, height, codec, frame = get_video_params(filepath, capture=True)
            h = shared.opts.extra_networks_card_size
            w = shared.opts.extra_networks_card_size if shared.opts.browser_fixed_width else width * h // height
            frame = frame.convert('RGB')
            frame.thumbnail((w, h), Image.Resampling.HAMMING)
            buffered = io.BytesIO()
            frame.save(buffered, format='jpeg')
            data_url = f'data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode("ascii")}'
            frame.close()
            content = {
                'exif': f'Codec: {codec}, Frames: {frames}, Duration: {duration:.2f} sec, FPS: {fps:.2f}',
                'data': data_url,
                'width': width,
                'height': height,
                'size': stat_size,
                'mtime': stat_mtime.timestamp() * 1000, # JS timestamps use milliseconds
            }
            return content
        except Exception as e:
            log.error(f'Gallery video: file="{filepath}" {e}')
            return {}

    def get_image_thumbnail(filepath, exif: bool = True):
        try:
            stat_size, stat_mtime = modelstats.stat(filepath)
            if stat_size < 1024:
                return {}
            with Image.open(filepath) as image:
                # 1. Grab original dimensions BEFORE draft mode alters them
                width, height = image.width, image.height
                if height == 0 or width == 0:
                    log.error(f"Image: file={filepath} {image} invalid")
                    return {}
                # 2. Extract EXIF data early
                geninfo = images.read_info_from_image(image)[0] if exif else None
                # 3. Calculate intended thumbnail size
                h = shared.opts.extra_networks_card_size
                w = shared.opts.extra_networks_card_size if shared.opts.browser_fixed_width else max(1, (width * h) // height)
                # 4. Apply JPEG Draft Mode which downsamples during load
                if image.format == "JPEG":
                    image.draft("RGB", (w, h))
                elif image.mode != 'RGB':
                    image = image.convert('RGB')
                # 5. Perform final precision thumbnail scale down
                image.thumbnail((w, h), Image.Resampling.HAMMING)
                # 6. Compress and encode to Base64
                buffered = io.BytesIO()
                image.save(buffered, format='JPEG', quality=85, optimize=True)
                b64_str = base64.b64encode(buffered.getbuffer()).decode("ascii")
                data_url = f'data:image/jpeg;base64,{b64_str}'
            content = {
                'exif': geninfo,
                'data': data_url,
                'width': width,   # Original width sent to client
                'height': height, # Original height sent to client
                'size': stat_size,
                'mtime': stat_mtime.timestamp() * 1000,
            }
            return content
        except Exception as e:
            log.error(f'Gallery image failed: file="{filepath}" | Error: {e}')
            return {}

    def ws_authenticated(ws: WebSocket):
        if not api.credentials and not getattr(shared.cmd_opts, 'auth_file', None):
            return True
        token = ws.cookies.get('access-token') or ws.cookies.get('access-token-unsecure')
        if token and hasattr(api.app, 'tokens') and (api.app.tokens is not None) and token in (api.app.tokens):
            return True
        auth_header = ws.headers.get('authorization')
        if auth_header and auth_header.lower().startswith('basic '):
            try:
                payload = base64.b64decode(auth_header.split(' ', 1)[1]).decode('utf-8')
                username, password = payload.split(':', 1)
            except Exception:
                return False
            if username in api.credentials and compare_digest(password.encode('utf-8'), api.credentials[username].encode('utf-8')):
                return True
            if hasattr(api.app, 'tokens') and (api.app.tokens is not None) and (password in api.app.tokens):
                return True
        return False

    # @app.get('/sdapi/v1/browser/folders', response_model=list[dict])
    def get_folders():
        def make_folder(path, label=None):
            """Create folder entry with path and display label."""
            if label is None:
                label = os.path.basename(path) or path
            return {"path": path, "label": label}

        reference_dir = os.path.join('models', 'Reference')
        base_samples = shared.opts.outdir_samples
        base_grids = shared.opts.outdir_grids
        # Build list of resolved output paths with labels
        folders = []
        if base_samples:
            base_samples = base_samples.rstrip('/\\')
            folders.append(make_folder(resolve_output_path(base_samples), "Folders"))
        if base_grids:
            base_grids = base_grids.rstrip('/\\')
            folders.append(make_folder(resolve_output_path(base_grids), "Folders"))
        # Use the specific folder setting values as labels (e.g., "outputs/text" -> "outputs/text")
        folders.append(make_folder(reference_dir, "Reference"))
        folders.append(make_folder(resolve_output_path(base_samples, shared.opts.outdir_txt2img_samples), shared.opts.outdir_txt2img_samples))
        folders.append(make_folder(resolve_output_path(base_samples, shared.opts.outdir_img2img_samples), shared.opts.outdir_img2img_samples))
        folders.append(make_folder(resolve_output_path(base_samples, shared.opts.outdir_control_samples), shared.opts.outdir_control_samples))
        folders.append(make_folder(resolve_output_path(base_samples, shared.opts.outdir_extras_samples), shared.opts.outdir_extras_samples))
        folders.append(make_folder(resolve_output_path(base_samples, shared.opts.outdir_save), shared.opts.outdir_save))
        folders.append(make_folder(resolve_output_path(base_samples, shared.opts.outdir_video), shared.opts.outdir_video))
        folders.append(make_folder(resolve_output_path(base_samples, shared.opts.outdir_init_images), shared.opts.outdir_init_images))
        folders.append(make_folder(resolve_output_path(base_grids, shared.opts.outdir_txt2img_grids), shared.opts.outdir_txt2img_grids))
        folders.append(make_folder(resolve_output_path(base_grids, shared.opts.outdir_img2img_grids), shared.opts.outdir_img2img_grids))
        folders.append(make_folder(resolve_output_path(base_grids, shared.opts.outdir_control_grids), shared.opts.outdir_control_grids))

        # Custom browser folders and reference dir
        custom_folder_paths = set()
        for f in shared.opts.browser_folders.split(','):
            f = f.strip()
            if f:
                folders.append(make_folder(f))
                custom_folder_paths.add(f)
        folders.append(make_folder(reference_dir, 'Reference'))
        # Filter empty and duplicates (by path)
        seen_paths = {}
        unique_folders = []
        for f in folders:
            path = f["path"].strip()
            if not path or not os.path.isdir(path):
                continue
            if path in seen_paths:
                if path in custom_folder_paths:
                    unique_folders[seen_paths[path]] = f
                continue
            seen_paths[path] = len(unique_folders)
            unique_folders.append(f)
            if (shared.demo is not None) and (path not in shared.demo.allowed_paths):
                debug(f'Browser folders allow: {path}')
                shared.demo.allowed_paths.append(path)
        if os.environ.get('SD_PATH_DEBUG', None):
            log.trace(f'Path allowed: why=gallery allowed={shared.demo.allowed_paths}')
        debug(f'Browser folders: {unique_folders}')
        return unique_folders

    def make_thumb(file: str, exif: bool = False):
        try:
            from modules.api import helpers
            fn = helpers.validate_path(file, shared.demo.allowed_paths)
            if fn.lower().endswith('.mp4'):
                return JSONResponse(content=get_video_thumbnail(fn))
            else:
                return JSONResponse(content=get_image_thumbnail(fn, exif))
        except Exception as e:
            log.error(f'Gallery: file="{file}" {e}')
            content = { 'error': str(e) }
            return JSONResponse(content=content)

    thumb_limiter: CapacityLimiter | None = None

    # @app.get("/sdapi/v1/browser/thumb", response_model=dict)
    async def get_thumb(file: str, exif: bool = False):
        nonlocal thumb_limiter
        if thumb_limiter is None: # created inside the event loop: older anyio cannot create one outside it
            thumb_limiter = CapacityLimiter(min(4, max(1, (os.cpu_count() or 1) // 2))) # decode off the event loop on at most half the cores: bounds memory with large images and leaves cpu for generation
        return await to_thread.run_sync(make_thumb, file, exif, limiter=thumb_limiter)

    # @app.get("/sdapi/v1/browser/files", response_model=list)
    async def ht_files(folder: str):
        try:
            t0 = time.time()
            from modules.api import helpers
            folder = helpers.validate_path(folder, allowed_folder=True)
            files = files_cache.directory_files(folder, recursive=True)
            lines = list(listing_lines(folder, files))
            t1 = time.time()
            log.debug(f'Gallery: type=ht folder="{folder}" files={len(lines)} time={t1-t0:.3f}')
            return lines
        except Exception as e:
            log.error(f'Gallery: {folder} {e}')
            return []

    api.add_api_route("/sdapi/v1/browser/folders", get_folders, methods=["GET"], response_model=list[ItemFolder])
    api.add_api_route("/sdapi/v1/browser/thumb", get_thumb, methods=["GET"], response_model=dict)
    api.add_api_route("/sdapi/v1/browser/files", ht_files, methods=["GET"], response_model=list)

    @api.app.websocket("/sdapi/v1/browser/files")
    async def ws_files(ws: WebSocket):
        if not ws_authenticated(ws):
            log.error(f'WS unauthorized: client={ws.client.host}')
            await ws.close(code=1008)
            return
        try:
            await manager.connect(ws)
            folder = await ws.receive_text()
            folder = unquote(folder).replace('%3A', ':')
            t0 = time.time()
            numFiles = 0
            files = list(files_cache.list_files(folder, recursive=True)) # snapshot: the loop below yields and cached file lists can be refreshed meanwhile
            # files.sort(key=os.path.getmtime)
            for msg in listing_lines(folder, files):
                numFiles += 1
                await manager.send(ws, msg)
                if numFiles % 100 == 0:
                    await asyncio.sleep(0) # let other requests run during long listings
            await manager.send(ws, '#END#')
            t1 = time.time()
            log.debug(f'Gallery: type=ws folder="{folder}" files={numFiles} time={t1-t0:.3f}')
        except Exception as e:
            debug(f'WS error: {e}')
        manager.disconnect(ws)

    get_folders() # initialize all folders
