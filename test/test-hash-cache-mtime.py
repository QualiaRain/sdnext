#!/usr/bin/env python
"""Offline regression tests for model hash cache invalidation.

Usage: python test/test-hash-cache-mtime.py
"""

import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('hash_cache_test_target', root / 'modules/hashes.py')
hashes = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {
    'modules.json_helpers': SimpleNamespace(readfile=lambda *_args, **_kwargs: {}, writefile=lambda *_args, **_kwargs: None),
    'modules.paths': SimpleNamespace(data_path=str(root)),
}):
    spec.loader.exec_module(hashes)


class HashCacheMtimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.filename = Path(self.temp.name) / 'model.safetensors'
        self.filename.write_bytes(b'original model')
        os.utime(self.filename, (2_000_000_000, 2_000_000_000))
        self.digest = hashlib.sha256(self.filename.read_bytes()).hexdigest()
        hashes._data.clear()  # pylint: disable=protected-access
        for store in (None, 'hashes-addnet'):
            hashes.cache(store).add_hash('model', self.filename.stat().st_mtime, self.digest)

    def test_unchanged_file_reuses_cached_digest(self):
        for store in (None, 'hashes-addnet'):
            with self.subTest(store=store):
                self.assertEqual(hashes.sha256_from_cache(self.filename, 'model', store=store), self.digest)

    def test_changed_mtime_invalidates_in_either_direction(self):
        self.filename.write_bytes(b'replacement model')
        for timestamp in (1_000_000_000, 2_100_000_000):
            os.utime(self.filename, (timestamp, timestamp))
            for store in (None, 'hashes-addnet'):
                with self.subTest(timestamp=timestamp, store=store):
                    self.assertIsNone(hashes.sha256_from_cache(self.filename, 'model', store=store))

    def test_missing_file_does_not_reuse_cached_digest(self):
        self.filename.unlink()
        for store in (None, 'hashes-addnet'):
            for timestamp in (2_000_000_000, 0):
                with self.subTest(store=store, timestamp=timestamp):
                    hashes.cache(store).add_hash('model', timestamp, self.digest)
                    self.assertIsNone(hashes.sha256_from_cache(self.filename, 'model', store=store))

    def test_uncached_or_empty_digest_remains_a_cache_miss(self):
        self.assertIsNone(hashes.sha256_from_cache(self.filename, 'unknown'))
        hashes.cache().add_hash('model', self.filename.stat().st_mtime, '')
        self.assertIsNone(hashes.sha256_from_cache(self.filename, 'model'))

    def test_sha256_rehashes_replacement_with_older_mtime(self):
        self.filename.write_bytes(b'replacement model')
        os.utime(self.filename, (1_000_000_000, 1_000_000_000))
        shared = SimpleNamespace(
            cmd_opts=SimpleNamespace(no_hashing=False),
            state=SimpleNamespace(begin=lambda *_args: 'hash-job', end=lambda *_args: None),
        )
        with patch.dict(sys.modules, {'modules.shared': shared}), patch.object(hashes, 'progress_ok', False):
            actual = hashes.sha256(self.filename, 'model')
        expected = hashlib.sha256(b'replacement model').hexdigest()
        self.assertEqual(actual, expected)
        self.assertEqual(hashes.cache()['model']['mtime'], self.filename.stat().st_mtime)
        self.assertEqual(hashes.sha256_from_cache(self.filename, 'model'), expected)


if __name__ == '__main__':
    unittest.main()
