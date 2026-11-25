#!/usr/bin/env python
"""
End-to-end generation check against a running SD.Next server.

Runs a fixed set of txt2img and img2img requests with fixed seeds, reports wall time per case and a sha256 of the
decoded pixels. Use it to show that a change keeps generated images bit-identical and to compare fixed overhead.
Hashes are only comparable between servers started the same way: same model, same torch thread count, same CPU or GPU.
With the tiny test model (see make_tiny_sd.py) fixed per-generation overhead dominates the timings.

Requires a running server with the model loaded.

Usage:
    venv/bin/python e2e.py [--url http://127.0.0.1:7860] [--runs 3] [--model Diffusers/tiny-sd] [--json out.json] [--compare ref.json]

With --compare the exit code is 1 when any hash differs from the reference file.
"""
import io
import sys
import json
import time
import base64
import hashlib
import argparse
import requests
from PIL import Image


def post(url, endpoint, payload, timeout=900):
    t0 = time.perf_counter()
    r = requests.post(f'{url}{endpoint}', json=payload, timeout=timeout)
    t1 = time.perf_counter()
    if r.status_code != 200:
        raise RuntimeError(f'{endpoint} status={r.status_code} body={r.text[:400]}')
    return r.json(), t1 - t0


def pixels_hash(b64):
    if ',' in b64[:64]:
        b64 = b64.split(',', 1)[1]
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    return hashlib.sha256(img.convert('RGB').tobytes()).hexdigest()[:16], img.size


def stats(times):
    times = sorted(times)
    return {'min': round(times[0], 4), 'median': round(times[len(times) // 2], 4), 'max': round(times[-1], 4)}


def run_case(args, endpoint, payload):
    times, hashes, size, res = [], set(), None, {}
    for _i in range(args.runs):
        res, t = post(args.url, endpoint, payload)
        times.append(t)
        for image in res.get('images', []):
            h, size = pixels_hash(image)
            hashes.add(h)
    return res, {'time': stats(times), 'first': round(times[0], 4), 'images': len(res.get('images', [])), 'size': size, 'hashes': sorted(hashes)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:7860')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--model', default='Diffusers/tiny-sd')
    parser.add_argument('--json', default=None, help='write results to this file')
    parser.add_argument('--compare', default=None, help='reference results file; exit 1 if any hash differs')
    args = parser.parse_args()
    out = {}

    opts = requests.get(f'{args.url}/sdapi/v1/options', timeout=60).json()
    if opts.get('sd_model_checkpoint') != args.model:
        _res, t = post(args.url, '/sdapi/v1/options', {'sd_model_checkpoint': args.model})
        out['set_model_s'] = round(t, 3)

    cases = {
        'txt2img_512_20': ('/sdapi/v1/txt2img', {'prompt': 'a photo of a cat, detailed', 'negative_prompt': 'blurry', 'seed': 42, 'steps': 20, 'width': 512, 'height': 512, 'cfg_scale': 6, 'sampler_name': 'Euler', 'batch_size': 1, 'save_images': False}),
        'txt2img_512_20_save': ('/sdapi/v1/txt2img', {'prompt': 'a photo of a cat, detailed', 'negative_prompt': 'blurry', 'seed': 42, 'steps': 20, 'width': 512, 'height': 512, 'cfg_scale': 6, 'sampler_name': 'Euler', 'batch_size': 1, 'save_images': True}),
        'txt2img_256_4': ('/sdapi/v1/txt2img', {'prompt': 'a photo of a dog', 'seed': 7, 'steps': 4, 'width': 256, 'height': 256, 'cfg_scale': 6, 'sampler_name': 'Euler', 'save_images': False}),
        'txt2img_512_20_batch4': ('/sdapi/v1/txt2img', {'prompt': 'landscape, mountains', 'seed': 123, 'steps': 20, 'width': 512, 'height': 512, 'cfg_scale': 6, 'sampler_name': 'Euler', 'batch_size': 4, 'save_images': False}),
    }
    first_image = None
    for name, (endpoint, payload) in cases.items():
        res, out[name] = run_case(args, endpoint, payload)
        if first_image is None and res.get('images'):
            first_image = res['images'][0]
        print(name, json.dumps(out[name]), flush=True)

    if first_image is not None:
        payload = {'prompt': 'a photo of a cat, watercolor', 'seed': 42, 'steps': 20, 'width': 512, 'height': 512, 'cfg_scale': 6, 'sampler_name': 'Euler', 'denoising_strength': 0.6, 'init_images': [first_image], 'save_images': False}
        _res, out['img2img_512_20'] = run_case(args, '/sdapi/v1/img2img', payload)
        print('img2img_512_20', json.dumps(out['img2img_512_20']), flush=True)

    if args.json:
        with open(args.json, 'w', encoding='utf8') as f:
            json.dump(out, f, indent=2)
    if args.compare:
        with open(args.compare, encoding='utf8') as f:
            ref = json.load(f)
        bad = [k for k, v in out.items() if isinstance(v, dict) and k in ref and v['hashes'] != ref[k]['hashes']]
        missing = [k for k in ref if isinstance(ref[k], dict) and k not in out]
        print(f'compare: reference={args.compare} differ={bad} missing={missing} result={"identical" if not bad and not missing else "DIFFERENT"}')
        return 1 if bad or missing else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
