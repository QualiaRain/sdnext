"""CPU regression for optional masking request fields, using the real API handler.

Run with the repository venv active:
    python test/test-mask-request-defaults.py
    python test/test-mask-request-defaults.py --repo ../baseline-worktree
Only unrelated runtime imports and segmentation inference are stubbed.
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


def stub(name, **attrs):
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
    return module


class Processing:
    def __init__(self):
        pass


stub('modules.processing', StableDiffusionProcessingTxt2Img=Processing, StableDiffusionProcessingImg2Img=Processing)
stub('modules.shared', parser=argparse.ArgumentParser(), sd_upscalers=[], state=MagicMock(),
     opts=types.SimpleNamespace(data={}, data_labels={}, typemap={}, samples_format='png', jpeg_quality=90))
stub('modules.errors', install=lambda: None)
stub('modules.logger', log=MagicMock())
stub('modules.postprocessing')
stub('modules.sd_samplers')
masking = stub('modules.masking', MODELS=['test'], TYPES=['Composite'],
               opts=types.SimpleNamespace(auto_mask=None), init_model=MagicMock(),
               run_mask=MagicMock(side_effect=lambda **kwargs: kwargs['input_image'].copy()))

from modules.api import process  # pylint: disable=wrong-import-position

app = FastAPI()
handler = process.APIProcess(Lock())
app.add_api_route('/sdapi/v1/mask', handler.post_mask, methods=['POST'], response_model=process.ResMask)
client = TestClient(app)
buffer = io.BytesIO()
Image.new('RGB', (2, 3), 'red').save(buffer, format='PNG')
image_b64 = base64.b64encode(buffer.getvalue()).decode('ascii')


class MaskRequestDefaults(unittest.TestCase):
    def setUp(self):
        masking.run_mask.reset_mock()
        masking.init_model.reset_mock()

    def assert_mask(self, payload):
        response = client.post('/sdapi/v1/mask', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        image = Image.open(io.BytesIO(base64.b64decode(response.json()['mask'])))
        self.assertEqual(image.size, (2, 3))
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))

    def test_builtin_cli_payload_omits_model(self):
        # cli/api-mask.py sends these fields and never sends model.
        self.assert_mask({'image': image_b64, 'mask': None, 'type': 'Composite', 'params': {'auto_mask': 'Grayscale'}})
        masking.init_model.assert_not_called()

    def test_auto_mask_omits_both_optional_fields(self):
        self.assert_mask({'image': image_b64, 'type': 'Composite'})
        self.assertIsNone(masking.run_mask.call_args.kwargs['input_mask'])
        masking.init_model.assert_not_called()

    def test_explicit_model_and_mask_preserved(self):
        self.assert_mask({'image': image_b64, 'mask': image_b64, 'model': 'test', 'type': 'Composite'})
        masking.init_model.assert_called_once_with('test')
        self.assertEqual(masking.run_mask.call_args.kwargs['input_mask'].size, (2, 3))

    def test_required_fields_still_required(self):
        for missing in ('image', 'type'):
            payload = {'image': image_b64, 'type': 'Composite'}
            del payload[missing]
            with self.subTest(missing=missing):
                response = client.post('/sdapi/v1/mask', json=payload)
                self.assertEqual(response.status_code, 422)
                self.assertIn(['body', missing], [error['loc'] for error in response.json()['detail']])
        masking.run_mask.assert_not_called()

    def test_openapi_marks_only_image_and_type_required(self):
        schema = app.openapi()['components']['schemas']['ReqMask']
        self.assertEqual(set(schema['required']), {'image', 'type'})


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], *remaining])
