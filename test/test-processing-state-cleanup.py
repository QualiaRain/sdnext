"""CPU regression: failed image-processing requests must end their API job.

Run with the repository venv active:
    python test/test-processing-state-cleanup.py
    python test/test-processing-state-cleanup.py --repo ../baseline-worktree
Uses real handlers, image encoding and shared State; model execution is stubbed.
"""
import argparse
import base64
import io
import sys
import types
import unittest
from pathlib import Path
from threading import Lock
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
args, remaining = parser.parse_known_args()
sys.path.insert(0, str(args.repo.resolve()))

import modules  # pylint: disable=wrong-import-position


def stub(name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    parent, _, child = name.rpartition('.')
    if parent in sys.modules:
        setattr(sys.modules[parent], child, module)
    return module


class Processing:
    def __init__(self):
        pass


stub('modules.processing', StableDiffusionProcessingTxt2Img=Processing, StableDiffusionProcessingImg2Img=Processing)
shared = stub('modules.shared', parser=argparse.ArgumentParser(), sd_upscalers=[],
              opts=types.SimpleNamespace(data={}, data_labels={}, typemap={}, samples_format='png', jpeg_quality=90))
stub('modules.errors', install=lambda: None, display=MagicMock())
stub('modules.logger', log=MagicMock())
stub('modules.postprocessing')
stub('modules.sd_samplers')
stub('modules.devices', torch_gc=MagicMock())
stub('modules.progress', current_task=None, pending_tasks=[])
masking = stub('modules.masking', MODELS=['test'], TYPES=['Composite'],
               opts=types.SimpleNamespace(), init_model=MagicMock(), run_mask=MagicMock())
stub('modules.control', processors=types.SimpleNamespace(config={'test': {'params': {}}}))

from modules.api import process  # pylint: disable=wrong-import-position
from modules.shared_state import State  # pylint: disable=wrong-import-position

app = FastAPI()
handler = process.APIProcess(Lock())
for route, fn in (('preprocess', handler.post_preprocess), ('mask', handler.post_mask), ('detect', handler.post_detect)):
    app.add_api_route(f'/sdapi/v1/{route}', fn, methods=['POST'])
client = TestClient(app, raise_server_exceptions=False)
buffer = io.BytesIO()
Image.new('RGB', (2, 3), 'red').save(buffer, format='PNG')
image_b64 = base64.b64encode(buffer.getvalue()).decode('ascii')


class ProcessingStateCleanup(unittest.TestCase):
    def setUp(self):
        shared.state = State()
        shared.state.state_history = []
        shared.opts.samples_format = 'png'
        process.processor = MagicMock(processor_id='test', return_value=Image.new('RGB', (2, 3)))
        masking.run_mask = MagicMock(return_value=Image.new('RGB', (2, 3)))
        shared.detailer = types.SimpleNamespace(predict=MagicMock(return_value=[]))

    def request(self, endpoint):
        return client.post(f'/sdapi/v1/{endpoint}', json={
            'image': image_b64, 'model': 'test', 'mask': None, 'type': 'Composite',
        })

    def assert_finished(self):
        self.assertEqual(shared.state.status().status, 'idle')
        self.assertEqual(shared.state.job_count, 0)
        self.assertFalse(shared.state.api)
        history = shared.state.state_history
        self.assertEqual([entry['op'] for entry in history], ['begin', 'end'])
        self.assertEqual(history[0]['id'], history[1]['id'])

    def test_successful_requests_end_their_job(self):
        for endpoint in ('preprocess', 'mask', 'detect'):
            with self.subTest(endpoint=endpoint):
                self.setUp()
                response = self.request(endpoint)
                self.assertEqual(response.status_code, 200, response.text)
                self.assert_finished()

    def test_preprocess_failure_ends_job(self):
        process.processor.side_effect = RuntimeError('processor failed')
        self.assertEqual(self.request('preprocess').status_code, 500)
        self.assert_finished()

    def test_mask_failure_ends_job(self):
        masking.run_mask.side_effect = RuntimeError('segmentation failed')
        self.assertEqual(self.request('mask').status_code, 500)
        self.assert_finished()

    def test_detect_failure_ends_job(self):
        shared.detailer.predict.side_effect = RuntimeError('detector failed')
        self.assertEqual(self.request('detect').status_code, 500)
        self.assert_finished()

    def test_preprocess_encoding_failure_ends_job(self):
        # Pillow cannot encode LA images as JPEG; exercise the real API encoder.
        shared.opts.samples_format = 'jpeg'
        process.processor.return_value = Image.new('LA', (2, 3))
        self.assertEqual(self.request('preprocess').status_code, 500)
        self.assert_finished()

    def test_detect_encoding_failure_ends_job(self):
        shared.opts.samples_format = 'jpeg'
        shared.detailer.predict.return_value = [types.SimpleNamespace(item=Image.new('LA', (2, 3)))]
        self.assertEqual(self.request('detect').status_code, 500)
        self.assert_finished()

    def test_mask_none_response_still_ends_job(self):
        masking.run_mask.return_value = None
        response = self.request('mask')
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json(), {'error': 'Mask is none'})
        self.assert_finished()


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *remaining])
