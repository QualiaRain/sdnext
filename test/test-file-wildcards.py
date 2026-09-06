"""Exercise the production style/wildcard path with real files, without loading models."""

import importlib
import logging
import random
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def wildcard_styles(tmp_path):
    # Only application startup dependencies are stubbed. Both styles.py and the
    # filesystem scanner are imported unchanged, and all wildcard parsing is real.
    package = ModuleType('modules')
    package.__path__ = [str(Path(__file__).resolve().parents[1] / 'modules')]
    shared = SimpleNamespace(
        opts=SimpleNamespace(wildcards_enabled=True, wildcards_dir=str(tmp_path)),
        state=SimpleNamespace(begin=lambda task: task, end=lambda _job: None),
    )
    stubs = {'modules': package, 'modules.shared': shared,
             'modules.logger': SimpleNamespace(log=logging.getLogger(__name__))}
    stubs.update({f'modules.{name}': ModuleType(f'modules.{name}') for name in ['infotext', 'sd_models', 'sd_vae']})
    with patch.dict(sys.modules, stubs):
        sys.modules.pop('modules.styles', None)
        sys.modules.pop('modules.files_cache', None)
        styles = importlib.import_module('modules.styles')
    database = styles.StyleDatabase.__new__(styles.StyleDatabase)
    database.styles = {}
    database.no_style = styles.Style('None')
    state = random.getstate()
    yield database
    random.setstate(state)


def expand(database, prompt, negative='', seed=123):
    # This is the same entry point and argument shape used by processing.py.
    positive, negatives = database.apply_styles_to_prompts([prompt], [negative], [], [seed])
    return positive[0], negatives[0]


def test_inline_choices_preserve_the_entire_line(wildcard_styles, tmp_path):
    (tmp_path / 'scene.txt').write_text(
        'forest, cabin, river, {morning|evening}, {rainy|misty}, {secluded|quiet}, {cozy|relaxing}\n',
        encoding='utf-8',
    )
    for seed in range(1, 11):
        positive, negative = expand(wildcard_styles, '__scene__', '__scene__', seed)
        for prompt in [positive, negative]:
            parts = prompt.split(', ')
            assert parts[:3] == ['forest', 'cabin', 'river']
            assert len(parts) == 7
            for value, choices in zip(parts[3:], [('morning', 'evening'), ('rainy', 'misty'), ('secluded', 'quiet'), ('cozy', 'relaxing')]):
                assert value in choices


def test_nested_weighted_choices_and_file_references(wildcard_styles, tmp_path):
    (tmp_path / 'scene.txt').write_text('a {__color__:1|blue:0} {cabin:0|{house:1|tent:0}} by a river\n', encoding='utf-8')
    (tmp_path / 'color.txt').write_text('{red:1|green:0}\n', encoding='utf-8')
    assert expand(wildcard_styles, '__scene__')[0] == 'a red house by a river'


@pytest.mark.parametrize('contents,expected', [
    ('red\ngreen\nblue\n', {'red', 'green', 'blue'}),
    ('red|green|blue\n', {'red', 'green', 'blue'}),
    ('[red|green|blue]\n', {'red', 'green', 'blue'}),
    ('# comment\n\nred # inline comment\n', {'red'}),
    ('a {red:1|green:0} cabin|a blue tent\n', {'a red cabin', 'a blue tent'}),
])
def test_existing_file_choices(wildcard_styles, tmp_path, contents, expected):
    (tmp_path / 'color.txt').write_text(contents, encoding='utf-8')
    for seed in range(1, 11):
        assert expand(wildcard_styles, '__color__', seed=seed)[0] in expected


def test_seeded_expansion_repeats_and_preserves_random_state(wildcard_styles, tmp_path):
    (tmp_path / 'color.txt').write_text('a {red|green|blue} cabin\na {white|black} tent\n', encoding='utf-8')
    before = random.getstate()
    first = expand(wildcard_styles, '__color__ and __color__', '__color__', seed=42)
    assert random.getstate() == before
    random.seed(9876)
    assert expand(wildcard_styles, '__color__ and __color__', '__color__', seed=42) == first


def test_missing_file_stays_unexpanded(wildcard_styles):
    assert expand(wildcard_styles, 'a __missing__ cabin')[0] == 'a __missing__ cabin'
