import unittest
from unittest import mock

from evdev import ecodes as e

from nocrosshair.core.input_loop import InputLoop, RawInputState, InputPipeline
from nocrosshair.core.controller import VirtualController
from nocrosshair.core.config import AppConfig
from nocrosshair.core.remapper import DEFAULT_KBD_BINDINGS


class DummyVirtualController(VirtualController):
    def __init__(self):
        self.device = None
        self.ctrl_type = "xbox360"
        self._lock = None
        self.written = []

    def write_button(self, button_code: int, value: int) -> None:
        self.written.append(("button", button_code, value))

    def write_axis(self, axis_code: int, value: int) -> None:
        self.written.append(("axis", axis_code, value))

    def write_trigger(self, axis_code: int, value: int) -> None:
        self.written.append(("trigger", axis_code, value))

    def reset(self) -> None:
        self.written.clear()


class DummyKeyboard:
    def __init__(self):
        self.written = []

    def write_key(self, key_code: int, value: int) -> None:
        self.written.append((key_code, value))

    def close(self) -> None:
        pass


class TestInputLoopKeyboardPassthrough(unittest.TestCase):

    def setUp(self):
        cfg = AppConfig()
        self.controller = DummyVirtualController()
        self.input_loop = InputLoop(cfg, self.controller, None, None)
        self.input_loop.virtual_keyboard = DummyKeyboard()

    def test_unmapped_keyboard_key_passthrough(self):
        from evdev import InputEvent

        event = InputEvent(0, 0, e.EV_KEY, e.KEY_Z, 1)
        self.input_loop._write_keyboard_passthrough(event, None)

        self.assertEqual(self.input_loop.virtual_keyboard.written, [(e.KEY_Z, 1)])

    def test_mapped_key_passthrough_when_no_conflict(self):
        """Teclas remapeadas SEM conflito passam pro teclado virtual — o jogo
        é KBM: se a tecla não chegar, 1-5/M/B/Tab param de funcionar.
        Só conflitos (F → BTN_Y) são consumidos."""
        from evdev import InputEvent

        event = InputEvent(0, 0, e.EV_KEY, e.KEY_SPACE, 1)
        self.input_loop._write_keyboard_passthrough(event, "BTN_A")

        self.assertEqual(self.input_loop.virtual_keyboard.written, [(e.KEY_SPACE, 1)])

    def test_mouse_button_not_passthrough(self):
        from evdev import InputEvent

        event = InputEvent(0, 0, e.EV_KEY, e.BTN_LEFT, 1)
        self.input_loop._write_keyboard_passthrough(event, "ABS_Z")

        self.assertEqual(self.input_loop.virtual_keyboard.written, [])


class TestInputLoopTapKeys(unittest.TestCase):
    def setUp(self):
        cfg = AppConfig()
        self.controller = DummyVirtualController()
        self.input_loop = InputLoop(cfg, self.controller, None, None)
        self.input_loop.virtual_keyboard = DummyKeyboard()

    def test_tap_key_press_does_not_release_immediately(self):
        """Q/F: press é escrito, mas o release NÃO pode sair no mesmo tick."""
        from evdev import InputEvent
        from nocrosshair.core.input_loop import TAP_HOLD_MS

        event = InputEvent(0, 0, e.EV_KEY, e.KEY_Q, 1)
        self.input_loop._handle_remap_key_event(event, "KEY_")

        writes = [(w[1], w[2]) for w in self.controller.written if w[0] == "button"]
        self.assertIn((e.BTN_B, 1), writes)
        self.assertNotIn((e.BTN_B, 0), writes, "release enviado no mesmo tick do press")
        self.assertIn("BTN_B", self.input_loop._pending_tap_releases)

    def test_f_key_not_passthrough_to_keyboard(self):
        """F (picareta) é remapeado → NÃO pode passar pro teclado virtual.
        Se passar, o jogo troca picareta 2x (tecla F + BTN_Y) e não segura."""
        from evdev import InputEvent

        press = InputEvent(0, 0, e.EV_KEY, e.KEY_F, 1)
        self.input_loop._handle_remap_key_event(press, "KEY_")

        self.assertNotIn((e.KEY_F, 1), self.input_loop.virtual_keyboard.written)
        writes = [(w[1], w[2]) for w in self.controller.written if w[0] == "button"]
        self.assertIn((e.BTN_Y, 1), writes)

    def test_weapon_key_1_passthrough_only(self):
        """KEY_1 não é remapeado: passa como tecla (slot 1 no KBM) e NÃO
        escreve RB — RB cicla arma e quebrava a seleção direta de slot."""
        from evdev import InputEvent

        press = InputEvent(0, 0, e.EV_KEY, e.KEY_1, 1)
        self.input_loop._handle_remap_key_event(press, "KEY_")

        self.assertIn((e.KEY_1, 1), self.input_loop.virtual_keyboard.written)
        writes = [(w[1], w[2]) for w in self.controller.written if w[0] == "button"]
        self.assertNotIn((e.BTN_TR, 1), writes)

    def test_tap_key_release_after_hold(self):
        """Q/F: após TAP_HOLD_MS, o flush escreve o release no controle virtual."""
        from evdev import InputEvent
        from nocrosshair.core.input_loop import TAP_HOLD_MS
        import time

        event = InputEvent(0, 0, e.EV_KEY, e.KEY_F, 1)
        self.input_loop._handle_remap_key_event(event, "KEY_")

        self.controller.written.clear()
        self.input_loop._flush_tap_releases(time.monotonic() + TAP_HOLD_MS / 1000.0 + 0.01)

        writes = [(w[1], w[2]) for w in self.controller.written if w[0] == "button"]
        self.assertIn((e.BTN_Y, 0), writes)
        self.assertNotIn("BTN_Y", self.input_loop._pending_tap_releases)

    def test_tap_key_physical_release_flushes_immediately(self):
        """Se o usuário soltar Q/F antes do hold, o release sai imediatamente."""
        from evdev import InputEvent
        import time

        press = InputEvent(0, 0, e.EV_KEY, e.KEY_Q, 1)
        self.input_loop._handle_remap_key_event(press, "KEY_")
        self.controller.written.clear()

        release = InputEvent(0, 0, e.EV_KEY, e.KEY_Q, 0)
        self.input_loop._handle_remap_key_event(release, "KEY_")

        writes = [(w[1], w[2]) for w in self.controller.written if w[0] == "button"]
        self.assertIn((e.BTN_B, 0), writes)
        self.assertNotIn("BTN_B", self.input_loop._pending_tap_releases)


class TestLoadoutSlots(unittest.TestCase):

    def setUp(self):
        self.cfg = AppConfig()
        self.controller = DummyVirtualController()
        self.input_loop = InputLoop(self.cfg, self.controller, None, None)
        self.pipeline = self.input_loop.pipeline

    def test_default_loadout_uses_user_weapons(self):
        self.assertEqual(
            self.pipeline.weapon_slots,
            [
                "Pickaxe",
                "EXTENDING FOCUS SHOTGUN",
                "SENTRY PISTOL",
                "PINNACLE RIFLE",
                "Sniper",
                "LMG",
            ],
        )

    def test_weapon_swap_selects_loadout_preset(self):
        self.pipeline.weapon_slots = [
            "Pickaxe", "WARFORGED AR", "SENTRY PISTOL", "PINNACLE RIFLE", "Sniper", "LMG",
        ]
        self.pipeline.handle_weapon_swap("KEY_2")
        self.assertEqual(self.pipeline.active_weapon_index, 2)
        engine = self.pipeline.anti_recoil_engine
        self.assertEqual(engine._weapon, "SENTRY PISTOL")
        self.assertIsNotNone(engine._pattern)

    def test_update_config_resyncs_loadout(self):
        self.cfg.recoil_runtime.loadout_slots = [
            "Pickaxe", "BANK SHOT PISTOL", "AUTO SHOTGUN", "MAVEN AUTO SHOTGUN", "Sniper", "LMG",
        ]
        self.input_loop.update_config(self.cfg)
        self.assertEqual(self.pipeline.weapon_slots[1], "BANK SHOT PISTOL")
        self.assertEqual(self.pipeline.weapon_slots[3], "MAVEN AUTO SHOTGUN")

    def test_short_loadout_gets_padded(self):
        self.cfg.recoil_runtime.loadout_slots = ["Pickaxe", "SENTRY PISTOL"]
        self.input_loop.update_config(self.cfg)
        self.assertEqual(len(self.pipeline.weapon_slots), 6)


class TestPipelineEngines(unittest.TestCase):

    def test_input_pipeline_exposes_rush_engine(self):
        """RushEngine deve estar instanciado (conserta AttributeError)."""
        cfg = AppConfig()
        pipeline = InputPipeline(cfg)
        self.assertIsNotNone(pipeline.rush_engine)
        self.assertEqual(pipeline.rush_engine.get_strafe(0.0), 0)

    def test_input_pipeline_exposes_aim_spam_engine(self):
        cfg = AppConfig()
        pipeline = InputPipeline(cfg)
        self.assertIsNotNone(pipeline.aim_spam_engine)


class TestAimAssistDisabled(unittest.TestCase):
    def test_aa_disabled_ignores_aa_only_remap_injection(self):
        cfg = AppConfig()
        cfg.remap_active = True
        cfg.aim_assist.enabled = False
        cfg.aim_assist.rush_enabled = True
        cfg.aim_assist.rush_always = True
        cfg.aim_assist.ls_freq_enabled = True
        cfg.aim_assist.ls_freq_amplitude = 20000
        cfg.aim_assist.strafe_shot_enabled = True
        cfg.aim_assist.strafe_shot_amplitude = 12000

        loop = InputLoop(cfg, DummyVirtualController(), None, None)
        loop._run_flush_remap(1_000_000.0)

        writes = [w for w in loop.controller.written if w[0] == "axis" and w[1] in (e.ABS_X, e.ABS_Y)]
        self.assertTrue(writes)
        self.assertEqual([v for _, _, v in writes], [0, 0])

    def test_mouse_does_not_write_right_stick_when_aa_disabled(self):
        from evdev import InputEvent

        cfg = AppConfig()
        cfg.aim_assist.enabled = False
        loop = InputLoop(cfg, DummyVirtualController(), None, None)
        loop._last_mouse_time = 0.0
        loop._mouse_dx = 200
        loop._mouse_dy = -80

        event = InputEvent(0, 0, e.EV_SYN, 0, 0)
        with mock.patch("nocrosshair.core.input_loop.time.monotonic", return_value=0.05):
            loop._handle_mouse_event(event)

        writes = [w for w in loop.controller.written if w[0] == "axis" and w[1] in (e.ABS_RX, e.ABS_RY)]
        self.assertEqual(writes, [("axis", e.ABS_RX, 0), ("axis", e.ABS_RY, 0)])


class TestKbmFireEngines(unittest.TestCase):
    """Rapid fire / bloom reducer no caminho KBM: o ciclo do gatilho precisa
    rodar no flush (hold do mouse), não só no evento de press."""

    def setUp(self):
        self.fake = {"now": 1_000_000.0}
        self.controller = DummyVirtualController()

    def _loop(self, rf_enabled=True, br_enabled=False, weapon="WARFORGED AR"):
        cfg = AppConfig()
        cfg.remap_active = True
        cfg.rapid_fire.enabled = rf_enabled
        cfg.bloom_reducer.enabled = br_enabled
        loop = InputLoop(cfg, self.controller, None, None)
        loop.pipeline.weapon_slots[1] = weapon
        loop.pipeline.active_weapon_index = 1
        return loop

    def _flush_cycle(self, loop, steps=6, step_ms=10.0):
        import nocrosshair.core.input_loop as il_mod
        import nocrosshair.features.rapid_fire as rf_mod
        import nocrosshair.features.bloom_reducer as br_mod

        def fake_monotonic():
            return self.fake["now"]

        rf_eng = loop.pipeline.rapid_fire_engine
        rf_eng.state.phase = "hold"
        rf_eng.state.last_transition = self.fake["now"]
        br_eng = loop.pipeline.bloom_reducer_engine
        br_eng._phase = "idle"
        br_eng._shots = 0
        br_eng._phase_start = self.fake["now"]

        values = []
        with mock.patch.object(il_mod.time, "monotonic", fake_monotonic), \
             mock.patch.object(rf_mod.time, "monotonic", fake_monotonic), \
             mock.patch.object(br_mod.time, "monotonic", fake_monotonic):
            for i in range(steps):
                self.fake["now"] = 1_000_000.0 + i * step_ms / 1000.0
                loop._run_flush_remap(self.fake["now"])
                for w in loop.controller.written:
                    if w[0] == "trigger" and w[1] == e.ABS_RZ:
                        values.append(w[2])
                loop.controller.reset()
        return values

    def test_hold_cycles_trigger_with_rapid_fire(self):
        loop = self._loop(weapon="TACTICAL SMG")
        loop.remap_pipeline.update_key("BTN_LEFT", 1)
        values = self._flush_cycle(loop)
        self.assertIn(255, values)
        self.assertIn(0, values)
        self.assertEqual(values[0], 255)

    def test_hold_cycles_trigger_with_bloom_reducer(self):
        loop = self._loop(rf_enabled=False, br_enabled=True, weapon="WARFORGED AR")
        loop.remap_pipeline.update_key("BTN_LEFT", 1)
        values = self._flush_cycle(loop)
        self.assertIn(255, values)
        self.assertIn(0, values)

    def test_weapon_auto_selects_rapid_fire_over_bloom(self):
        cfg = AppConfig()
        cfg.rapid_fire.enabled = True
        cfg.bloom_reducer.enabled = True
        loop = InputLoop(cfg, self.controller, None, None)
        loop.pipeline.weapon_slots[1] = "TACTICAL SMG"
        loop.pipeline.active_weapon_index = 1
        loop.remap_pipeline.update_key("BTN_LEFT", 1)
        self._flush_cycle(loop, steps=6, step_ms=10.0)
        self.assertEqual(loop.pipeline.rapid_fire_engine.state.phase, "hold")

    def test_release_writes_zero(self):
        loop = self._loop(weapon="TACTICAL SMG")
        loop.remap_pipeline.update_key("BTN_LEFT", 1)
        self._flush_cycle(loop, steps=2, step_ms=10.0)
        loop.controller.reset()
        loop._write_mapped("ABS_RZ", 0)
        written = [w for w in loop.controller.written if w[0] == "trigger" and w[1] == e.ABS_RZ]
        self.assertTrue(written)
        self.assertEqual(written[-1][2], 0)

    def test_no_trigger_pressed_writes_nothing(self):
        loop = self._loop(weapon="WARFORGED AR")
        self._flush_cycle(loop, steps=3)
        written = [w for w in loop.controller.written if w[0] == "trigger"]
        self.assertEqual(written, [])


if __name__ == "__main__":
    unittest.main()
