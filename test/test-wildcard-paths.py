"""File wildcard paths must match complete path components, as documented in Wildcards.md."""

import importlib
import logging
import ntpath
import random
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import mock_open, patch

import pytest


@pytest.fixture
def styles(tmp_path):
    # Load the production parser and filesystem scanner without application startup.
    package = ModuleType('modules')
    package.__path__ = [str(Path(__file__).resolve().parents[1] / 'modules')]
    shared = SimpleNamespace(opts=SimpleNamespace(wildcards_enabled=True, wildcards_dir=str(tmp_path)))
    stubs = {'modules': package, 'modules.shared': shared,
             'modules.logger': SimpleNamespace(log=logging.getLogger(__name__))}
    stubs.update({f'modules.{name}': ModuleType(f'modules.{name}') for name in ['infotext', 'sd_models', 'sd_vae']})
    with patch.dict(sys.modules, stubs):
        sys.modules.pop('modules.styles', None)
        sys.modules.pop('modules.files_cache', None)
        module = importlib.import_module('modules.styles')
    state = random.getstate()
    yield module
    random.setstate(state)


def write_wildcard(root, name, contents='red'):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding='utf-8')
    return path


@pytest.mark.parametrize('filename,reference', [
    ('othernsp/color.txt', 'nsp/color'),
    ('nsp/color-extra.txt', 'nsp/color'),
    ('othernsp/color.txt', 'nsp/'),
    ('othernsp/sub/color.txt', 'nsp/sub/'),
])
def test_partial_path_does_not_match(styles, tmp_path, filename, reference):
    write_wildcard(tmp_path, filename)
    prompt = f'__{reference}__'
    assert styles.apply_file_wildcards(prompt)[0] == prompt


@pytest.mark.parametrize('filename,reference', [
    ('nsp/color.txt', 'nsp/color'),
    ('nsp/color.txt', 'nsp\\color'),
    ('nsp/sub/color.txt', 'nsp/sub\\color'),
    ('nsp/color.txt', 'color'),
    ('nsp/color.txt', 'nsp/'),
    ('nsp/color.txt', 'nsp\\'),
    ('nsp/sub/color.txt', 'nsp/'),
    ('nsp/sub/color.txt', 'nsp/sub/'),
    ('nsp/sub/color.txt', 'nsp'),
    ('nsp/color/sub/file.txt', 'nsp/color'),
])
def test_documented_file_and_directory_references(styles, tmp_path, filename, reference):
    write_wildcard(tmp_path, filename)
    assert styles.apply_file_wildcards(f'__{reference}__')[0] == 'red'


def test_absolute_paths(styles, tmp_path):
    path = write_wildcard(tmp_path, 'nsp/color.txt')
    assert styles.apply_file_wildcards(f'__{path.with_suffix("")}__')[0] == 'red'
    assert styles.apply_file_wildcards(f'__{path.parent}/__')[0] == 'red'


def test_exact_reference_cannot_select_a_nearby_directory(styles, tmp_path):
    wrong = write_wildcard(tmp_path, 'othernsp/color.txt', 'blue')
    right = write_wildcard(tmp_path, 'nsp/color.txt', 'red')
    # Scan order varies by filesystem; deliberately put the false match first.
    with patch.object(styles.files_cache, 'list_files', return_value=[str(wrong), str(right)]):
        assert styles.apply_file_wildcards('__nsp/color__')[0] == 'red'


def test_exact_file_precedes_directory_fallback(styles, tmp_path):
    directory = write_wildcard(tmp_path, 'nsp/color/child.txt', 'blue')
    file = write_wildcard(tmp_path, 'nsp/color.txt', 'red')
    with patch.object(styles.files_cache, 'list_files', return_value=[str(directory), str(file)]):
        assert styles.apply_file_wildcards('__nsp/color__')[0] == 'red'


@pytest.mark.parametrize('reference,expected', [
    ('nsp/color', 'red'),
    ('nsp\\color', 'red'),
    ('nsp/', 'red'),
    ('C:\\wildcards\\nsp\\color', 'red'),
    ('sp/color', '__sp/color__'),
])
def test_windows_path_components(styles, reference, expected):
    # Exercise Windows path semantics on any OS; only Windows file I/O is stubbed.
    with patch.object(styles, 'os', SimpleNamespace(path=ntpath)), \
         patch.object(styles.files_cache, 'list_files', return_value=['C:\\wildcards\\nsp\\color.txt']), \
         patch('builtins.open', mock_open(read_data='red')):
        assert styles.apply_file_wildcards(f'__{reference}__')[0] == expected
