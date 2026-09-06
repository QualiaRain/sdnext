"""Exercise seed-zero prompt expansion through the generation entry point, without models."""

import importlib
import logging
from pathlib import Path
import random
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def style_database(tmp_path):
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
    database.styles = {'colors': styles.Style('colors', wildcards='COLOR=red,green,blue,yellow')}
    database.no_style = styles.Style('None')
    state = random.getstate()
    yield database
    random.setstate(state)


def expand(database, prompt, selected_styles, seeds):
    # processing.py supplies positive prompts, negative prompts, style names and per-image seeds.
    return database.apply_styles_to_prompts([prompt] * len(seeds), [prompt] * len(seeds), selected_styles, seeds)


@pytest.mark.parametrize('seed', [0, 123])
@pytest.mark.parametrize('prompt,selected_styles', [
    ('{red|green|blue|yellow}', []),
    ('COLOR', ['colors']),
    ('__colors__', []),
])
def test_seeded_generation_is_independent_of_ambient_random_state(style_database, tmp_path, seed, prompt, selected_styles):
    (tmp_path / 'colors.txt').write_text('red\ngreen\nblue\nyellow\n', encoding='utf-8')
    outputs = []
    for ambient_seed in range(8):
        random.seed(ambient_seed)
        before = random.getstate()
        outputs.append(expand(style_database, prompt, selected_styles, [seed]))
        assert random.getstate() == before
    assert all(output == outputs[0] for output in outputs)
    assert outputs[0][0] == outputs[0][1]  # Both positive and negative prompts use the image seed.


def test_repeated_zero_seed_in_batch_uses_same_file_choice(style_database, tmp_path):
    (tmp_path / 'colors.txt').write_text('red\ngreen\nblue\nyellow\n', encoding='utf-8')
    positive, negative = expand(style_database, '__colors__', [], [0, 123, 0])
    expected = [random.Random(seed).choice(['red', 'green', 'blue', 'yellow']) for seed in [0, 123, 0]]
    assert positive == expected
    assert negative == expected


def test_unspecified_seed_still_uses_ambient_random_state(style_database, tmp_path):
    colors = ['red', 'green', 'blue', 'yellow']
    (tmp_path / 'colors.txt').write_text('\n'.join(colors) + '\n', encoding='utf-8')
    for ambient_seed in range(8):
        random.seed(ambient_seed)
        reference = random.Random(ambient_seed)
        before = random.getstate()
        assert expand(style_database, '__colors__', [], [-1]) == ([reference.choice(colors)], [reference.choice(colors)])
        assert random.getstate() == before
