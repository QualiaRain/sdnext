"""History capacity regressions without loading inference dependencies."""

import importlib.util
import logging
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


root = Path(__file__).resolve().parents[1]
package = ModuleType('modules')
package.__path__ = [str(root / 'modules')]
shared = SimpleNamespace(opts=SimpleNamespace(latent_history=20), state=SimpleNamespace(latent_history=0))
spec = importlib.util.spec_from_file_location('history_capacity_target', root / 'modules/history.py')
history = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {
    'modules': package,
    'modules.shared': shared,
    'modules.devices': SimpleNamespace(cpu='cpu', device='cpu'),
    'modules.logger': SimpleNamespace(log=logging.getLogger(__name__)),
    'torch': SimpleNamespace(Tensor=type('Tensor', (), {}), is_tensor=lambda _value: False),
}):
    spec.loader.exec_module(history)


class HistoryCapacityTests(unittest.TestCase):
    def setUp(self):
        shared.opts.latent_history = 20
        shared.state.latent_history = 0
        self.history = history.History()

    def add_image_result(self, number):
        # Matches processing.py's post-save call: no latent, with image results.
        self.history.add(None, info=[str(number)], ops=['txt2img'], images=[number])

    def test_capacity_one_retains_latest_result(self):
        shared.opts.latent_history = 1
        self.add_image_result(1)
        self.assertEqual(self.history.last_image, [1])
        self.add_image_result(2)
        self.assertEqual(self.history.count, 1)
        self.assertEqual(self.history.last_image, [2])

    def test_default_capacity_preserves_twenty_newest_results(self):
        for number in range(25):
            self.add_image_result(number)
        self.assertEqual(self.history.count, 20)
        self.assertEqual([item.images[0] for item in self.history.latents], list(range(24, 4, -1)))

    def test_lowering_capacity_trims_existing_entries_on_next_add(self):
        for number in range(10):
            self.add_image_result(number)
        shared.opts.latent_history = 2
        self.add_image_result(10)
        self.assertEqual([item.images[0] for item in self.history.latents], [10, 9])

    def test_disabled_history_does_not_add_items(self):
        shared.opts.latent_history = 0
        self.add_image_result(1)
        self.assertEqual(self.history.count, 0)
        self.assertEqual(shared.state.latent_history, 1)

    def test_increasing_capacity_retains_available_results(self):
        shared.opts.latent_history = 2
        self.add_image_result(1)
        shared.opts.latent_history = 4
        self.add_image_result(2)
        self.add_image_result(3)
        self.assertEqual([item.images[0] for item in self.history.latents], [3, 2, 1])


if __name__ == '__main__':
    unittest.main()
