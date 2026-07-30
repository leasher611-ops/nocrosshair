import time
import pytest
from nocrosshair.core.macro import (
    MacroPlayer, MacroRecorder, Macro, MacroAction, MacroActionType
)


class TestMacroPlayer:

    def _make_macro(self, n=3):
        actions = [
            MacroAction(action_type=MacroActionType.PRESS, target=f"btn{i}", duration=0)
            for i in range(n)
        ]
        timing = [50 * i for i in range(n)]
        return Macro(name="test", trigger="KEY_A", actions=actions, timing=timing)

    def test_play_iterates_all_actions(self):
        macro = self._make_macro(3)
        player = MacroPlayer()
        player.play(macro)

        results = []
        while player.is_playing():
            action = player.get_next_action()
            if action is None:
                break
            results.append(action)
            player.advance()

        assert len(results) == 3
        assert results[0].target == "btn0"
        assert results[1].target == "btn1"
        assert results[2].target == "btn2"

    def test_stop_halts(self):
        macro = self._make_macro(3)
        player = MacroPlayer()
        player.play(macro)

        action = player.get_next_action()
        assert action is not None

        player.stop()
        assert player.is_playing() is False
        assert player.get_next_action() is None


class TestMacroRecorder:

    def test_record_and_stop_returns_macro(self):
        recorder = MacroRecorder()
        recorder.start_recording("TestMacro")
        assert recorder.is_recording() is True

        recorder.record_action(MacroActionType.PRESS, "btn_a")
        time.sleep(0.02)
        recorder.record_action(MacroActionType.RELEASE, "btn_a")

        macro = recorder.stop_recording()
        assert macro is not None
        assert macro.name == "TestMacro"
        assert len(macro.actions) == 2
        assert recorder.is_recording() is False

    def test_stop_without_start_returns_none(self):
        recorder = MacroRecorder()
        result = recorder.stop_recording()
        assert result is None

    def test_stop_without_actions_returns_none(self):
        recorder = MacroRecorder()
        recorder.start_recording("EmptyMacro")
        macro = recorder.stop_recording()
        assert macro is None

    def test_record_action_not_recording(self):
        recorder = MacroRecorder()
        recorder.record_action(MacroActionType.PRESS, "btn_a")
        assert len(recorder.get_recorded_actions()) == 0
