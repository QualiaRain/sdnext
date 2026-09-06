#!/usr/bin/env python
"""Offline regression tests for filename pattern arguments.

Usage: python test/test-namegen-patterns.py
"""

import datetime
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
# Filename expansion needs settings, but no model or application startup.
with patch.dict(sys.modules, {
    'modules.shared': SimpleNamespace(opts=SimpleNamespace(data={})),
    'modules.errors': SimpleNamespace(display=lambda *_args: None),
}):
    spec.loader.exec_module(namegen)


class FixedDatetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 9, 6, 1, 30, tzinfo=datetime.timezone.utc)
        return value.astimezone(tz) if tz is not None else value


class FilenamePatternTests(unittest.TestCase):
    def setUp(self):
        self.generator = namegen.FilenameGenerator(
            p=SimpleNamespace(width=64, height=64),
            seed=42,
            prompt='A cat beneath the moon',
        )

    def test_datetime_format(self):
        with patch.object(namegen.datetime, 'datetime', FixedDatetime):
            self.assertEqual(self.generator.apply('image-[datetime<%Y>].png'), 'image-2026.png')

    def test_datetime_format_and_timezone(self):
        with patch.object(namegen.datetime, 'datetime', FixedDatetime):
            self.assertEqual(self.generator.apply('[datetime<%Y-%m-%d_%H%M><America/New_York>]'), '2026-09-05_2130')

    def test_pattern_names_remain_case_insensitive(self):
        with patch.object(namegen.datetime, 'datetime', FixedDatetime):
            self.assertEqual(self.generator.apply('[DATETIME<%Y>]'), '2026')

    def test_hasprompt_arguments_keep_order(self):
        self.assertEqual(self.generator.apply('[hasprompt<cat|dog><sun|moon>]'), 'catmoon')

    def test_hasprompt_without_match_or_default(self):
        self.assertEqual(self.generator.apply('image[hasprompt<dog>].png'), 'image.png')

    def test_plain_pattern_and_literal_text(self):
        self.assertEqual(self.generator.apply('image-[seed].png'), 'image-42.png')

    def test_unknown_pattern_preserves_arguments(self):
        self.assertEqual(self.generator.apply('image-[unknown<value>].png'), 'image-[unknown<value>].png')


if __name__ == '__main__':
    unittest.main()
