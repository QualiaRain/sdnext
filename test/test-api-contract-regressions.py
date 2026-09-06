"""CPU reproductions using real API registration, request/response models and handlers.

Only model execution and unrelated server/GPU/UI imports are replaced. Run from
the repository root with its venv active:
    python test/test-api-contract-regressions.py
    python test/test-api-contract-regressions.py --repo ../baseline-worktree
"""
import argparse
import base64
import importlib
import io
import sys
import types
from pathlib import Path
from threading import Lock
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
args = parser.parse_args()
sys.path.insert(0, str(args.repo.resolve()))


def stub(name, **attrs):
    value = types.ModuleType(name)
    value.__dict__.update(attrs)
    sys.modules[name] = value
    return value


class Processing:
    def __init__(self):
        pass


shared = stub('modules.shared',
              sd_upscalers=[],
              parser=argparse.ArgumentParser(),
              opts=types.SimpleNamespace(data={}, data_labels={}, typemap={},
                                         subpath='', samples_format='png', jpeg_quality=90,
                                         autocomplete_dir=''),
              state=MagicMock())
stub('modules.processing', StableDiffusionProcessingTxt2Img=Processing,
     StableDiffusionProcessingImg2Img=Processing)
stub('modules.errors', install=lambda: None)
stub('modules.logger', log=MagicMock())
stub('modules.paths', models_path='models')
stub('modules.postprocessing')
for name in ('devices', 'images', 'sd_models', 'sd_samplers', 'sd_vae',
             'sd_hijack_hypertile', 'processing_vae', 'timer'):
    stub(f'modules.{name}')
stub('torch')
stub('cv2')

from modules.api import process  # pylint: disable=wrong-import-position
from modules import processing_helpers  # pylint: disable=wrong-import-position

for name in ('endpoints', 'script', 'server', 'generate', 'control', 'video', 'docs', 'gpu',
             'options', 'caption', 'loras', 'autocomplete', 'gallery', 'nudenet',
             'xyz_grid', 'upload', 'validate'):
    sys.modules[f'modules.api.{name}'] = MagicMock()
stub('modules.civitai', api_civitai=MagicMock())
stub('modules.rembg', rembg_api=MagicMock())
api_module = importlib.import_module('modules.api.api')

api = api_module.Api.__new__(api_module.Api)
api.app = FastAPI()
api.credentials = {}
api.queue_lock = Lock()
api.process = process.APIProcess(api.queue_lock)
api.generate = MagicMock()
api.control = MagicMock()
api.video = MagicMock()
real_add_route = api.add_api_route


def register_test_route(path, fn, **kwargs):
    # Execute the actual register() source so the test fails if its response_model
    # disagrees with the real handler. Other routes are outside this reproduction.
    if path in ('/sdapi/v1/preprocess', '/sdapi/v1/prompt-enhance'):
        real_add_route(path, fn, **kwargs)


api.add_api_route = register_test_route
api.register()


class IdentityProcessor:
    def __init__(self, processor_id):
        self.processor_id = processor_id

    def __call__(self, image, local_config):
        assert local_config == {}
        return image.copy()


stub('modules.control', processors=types.SimpleNamespace(
    config={'test': {'params': {}}}, Processor=IdentityProcessor))
enhance = MagicMock(return_value='enhanced prompt')
stub('modules.scripts_manager', scripts_control=types.SimpleNamespace(scripts=[
    types.SimpleNamespace(filename='scripts/prompt_enhance_ext.py', enhance=enhance)]))

client = TestClient(api.app, raise_server_exceptions=False)
failures = []

image = Image.new('RGB', (2, 3), 'red')
buffer = io.BytesIO()
image.save(buffer, format='PNG')
response = client.post('/sdapi/v1/preprocess', json={
    'model': 'test', 'image': base64.b64encode(buffer.getvalue()).decode('ascii')})
if response.status_code != 200:
    failures.append('preprocess response model')
    print(f'FAIL preprocess: HTTP {response.status_code} {response.text}')
else:
    payload = response.json()
    result = Image.open(io.BytesIO(base64.b64decode(payload['image'])))
    assert payload['model'] == 'test'
    assert result.size == (2, 3) and result.getpixel((0, 0)) == (255, 0, 0)
    print('PASS preprocess: HTTP 200 with model and valid PNG image')
schema = api.app.openapi()
ref = schema['paths']['/sdapi/v1/preprocess']['post']['responses']['200']['content']['application/json']['schema']['$ref']
response_schema = schema['components']['schemas'][ref.rsplit('/', 1)[-1]]
print('Preprocess response properties:', sorted(response_schema['properties']))
print('Preprocess response required fields:', response_schema.get('required', []))

for supplied, expected in ((0, 0), (42, 42), (-1, 1234567), (None, 1234567)):
    request = {'prompt': 'a castle'}
    if supplied is not None:
        request['seed'] = supplied
    enhance.reset_mock()
    # The real get_fixed_seed is used, with randomness fixed only for deterministic
    # assertions that the sentinel takes the random path and zero does not.
    with patch.object(processing_helpers.random, 'seed'), patch.object(processing_helpers.random, 'randrange', return_value=1234567):
        response = client.post('/sdapi/v1/prompt-enhance', json=request)
    assert response.status_code == 200, response.text
    actual = response.json()['seed']
    assert enhance.call_args.kwargs['seed'] == actual
    if actual != expected:
        failures.append(f'prompt seed {supplied}')
        print(f'FAIL prompt seed {supplied}: returned/passed {actual}, expected {expected}')
    else:
        print(f'PASS prompt seed {supplied}: returned/passed {actual}')

raise SystemExit(bool(failures))
