#!/usr/bin/env python
"""Offline regression tests for seed values in image filenames.

Usage: python test/test-namegen-seed.py
"""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('namegen_test_target', root / 'modules/image/namegen.py')
namegen = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {
    'modules.shared': SimpleNamespace(opts=SimpleNamespace(data={})),
    'modules.errors': SimpleNamespace(display=lambda *_args: None),
}):
    spec.loader.exec_module(namegen)


class FilenameSeedTests(unittest.TestCase):
    def test_explicit_zero_in_batch_uses_current_image_seed(self):
        processing = SimpleNamespace(width=64, height=64, all_seeds=[123, 0], seeds=[123, 0])
        # The main image save passes p.seeds[i] as the explicit seed.
        filenames = [namegen.FilenameGenerator(p=processing, seed=seed).apply('image-[seed].png') for seed in processing.seeds]
        self.assertEqual(filenames, ['image-123.png', 'image-0.png'])

    def test_explicit_zero_in_single_image(self):
        processing = SimpleNamespace(width=64, height=64, seed=0)
        self.assertEqual(namegen.FilenameGenerator(p=processing, seed=0).apply('[seed]'), '0')

    def test_zero_from_processing_seed_fallbacks(self):
        for seed_fields in ({'all_seeds': [0]}, {'seeds': [0]}, {'seed': 0}):
            with self.subTest(seed_fields=seed_fields):
                processing = SimpleNamespace(width=64, height=64, **seed_fields)
                self.assertEqual(namegen.FilenameGenerator(p=processing).apply('[seed]'), '0')

    def test_unspecified_seed_still_uses_processing_seed(self):
        processing = SimpleNamespace(width=64, height=64, all_seeds=[123])
        for seed in (None, -1):
            with self.subTest(seed=seed):
                self.assertEqual(namegen.FilenameGenerator(p=processing, seed=seed).apply('[seed]'), '123')

    def test_no_processing_object_has_no_seed(self):
        self.assertEqual(namegen.FilenameGenerator().apply('image[seed].png'), 'image.png')


if __name__ == '__main__':
    unittest.main()
