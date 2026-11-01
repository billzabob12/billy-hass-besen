"""Regression tests without Home Assistant or physical charger access."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).parents[1] / "custom_components/besen/status_health.py"
spec = importlib.util.spec_from_file_location("status_health", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class HealthTests(unittest.TestCase):
    def test_metadata_does_not_extend_charge_freshness(self):
        with patch.object(mod.time, "monotonic", return_value=0):
            health = mod.ChargeStatusHealth()
        with patch.object(mod.time, "monotonic", return_value=91):
            health.observe_live(None)
            self.assertFalse(health.fresh)
            self.assertTrue(health.recover_due())
            self.assertFalse(health.recover_due())

    def test_fresh_charge_report_recovers_even_when_values_are_unchanged(self):
        with patch.object(mod.time, "monotonic", return_value=0):
            health = mod.ChargeStatusHealth()
        with patch.object(mod.time, "monotonic", return_value=91):
            health.observe_live(91)
            self.assertTrue(health.fresh)
            self.assertEqual(health.age, 0)

    def test_disconnect_copy_does_not_count_as_measurement(self):
        with patch.object(mod.time, "monotonic", return_value=0):
            health = mod.ChargeStatusHealth()
        with patch.object(mod.time, "monotonic", return_value=91):
            health.observe_live(None)
            self.assertFalse(health.fresh)

    def test_recovery_is_bounded_and_never_sends_a_charge_command(self):
        with patch.object(mod.time, "monotonic", return_value=0):
            health = mod.ChargeStatusHealth()
        for now, expected in [
            (89, False),
            (90, True),
            (100, False),
            (269, False),
            (270, True),
        ]:
            with patch.object(mod.time, "monotonic", return_value=now):
                self.assertEqual(health.recover_due(), expected)
