"""CPU-only regression tests for inline choices inside wildcard files.

Runs the production styles module with model-dependent imports stubbed.
Run with: python test/test-file-inline-wildcards.py
"""
import importlib.util
import pathlib
import random
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))


class TestFileInlineWildcards(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = pathlib.Path(self.directory.name)
        self.random_state = random.getstate()
        self.addCleanup(random.setstate, self.random_state)
        stubs = {
            'modules.files_cache': SimpleNamespace(list_files=lambda *_args, **_kwargs: sorted(str(p) for p in self.folder.glob('*.txt'))),
            'modules.shared': SimpleNamespace(opts=SimpleNamespace(wildcards_enabled=True, wildcards_dir=str(self.folder))),
            'modules.infotext': Mock(),
            'modules.sd_models': Mock(),
            'modules.sd_vae': Mock(),
            'modules.logger': SimpleNamespace(log=Mock()),
        }
        with patch.dict(sys.modules, stubs):
            spec = importlib.util.spec_from_file_location('styles_under_test', root / 'modules' / 'styles.py')
            self.styles = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.styles)

    def expand(self, line, seed=1):
        (self.folder / 'scene.txt').write_text(line + '\n', encoding='utf-8')
        random.seed(seed)
        return self.styles.apply_wildcards_to_prompt('prefix __scene__ suffix', [], silent=True)

    def test_inline_choices_preserve_surrounding_text(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                result = self.expand('forest, {morning|evening}, {rainy|misty}, cabin', seed)
                self.assertRegex(result, r'^prefix forest, (morning|evening), (rainy|misty), cabin suffix$')

    def test_weighted_choice(self):
        self.assertEqual(self.expand('forest, {morning:0|evening:1}, cabin'), 'prefix forest, evening, cabin suffix')

    def test_nested_choice(self):
        self.assertRegex(self.expand('forest, {morning|{evening|night}}, cabin'), r'^prefix forest, (morning|evening|night), cabin suffix$')

    def test_legacy_pipe_choices(self):
        for line in ('morning|evening', '[morning|evening]'):
            with self.subTest(line=line):
                self.assertRegex(self.expand(line), r'^prefix (morning|evening) suffix$')

    def test_recursive_file_choice(self):
        (self.folder / 'weather.txt').write_text('rainy\n', encoding='utf-8')
        self.assertEqual(self.expand('forest, {__weather__:1|sunny:0}, cabin'), 'prefix forest, rainy, cabin suffix')

    def test_plain_line_and_comments(self):
        self.assertEqual(self.expand('forest, cabin # comment'), 'prefix forest, cabin suffix')


if __name__ == '__main__':
    unittest.main()
