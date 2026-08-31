import pytest

from nocrosshair.core.config import CrouchAimConfig
from nocrosshair.features.crouch_aim import CrouchAimEngine


def _engine(enabled=True, button_code=0x13E):
    cfg = CrouchAimConfig(enabled=enabled, button_code=button_code)
    eng = CrouchAimEngine(cfg)
    eng.set_active(enabled)
    return eng


class TestCrouchAimEngine:

    def test_disabled_no_output(self):
        eng = _engine(enabled=False)
        assert eng.process(True) is None
        assert eng.is_active is False

    def test_aiming_presses_crouch(self):
        eng = _engine()
        assert eng.process(True) is True
        assert eng.get_button_code() == 0x13E

    def test_no_change_returns_none(self):
        eng = _engine()
        eng.process(True)
        assert eng.process(True) is None

    def test_release_stands(self):
        eng = _engine()
        eng.process(True)
        assert eng.process(False) is False

    def test_deactivate_while_holding_releases(self):
        eng = _engine()
        eng.process(True)
        eng.set_active(False)
        assert eng.process(False) is False
        assert eng.process(False) is None

    def test_toggle(self):
        eng = _engine(enabled=False)
        assert eng.toggle() is True
        assert eng.process(True) is True

    def test_update_config_disables(self):
        eng = _engine()
        eng.update_config(CrouchAimConfig(enabled=False))
        assert eng.is_active is False