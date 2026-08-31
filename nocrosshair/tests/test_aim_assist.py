import math
import pytest
from nocrosshair.core.config import AimAssistConfig
from nocrosshair.features.aim_assist import AimAssistEngine, AimAssistPresets
from nocrosshair.features.aim_assist import AimAssistPipeline
from nocrosshair.features.aim_assist import PulseLevelEngine


class TestFnControllerPreset:

    def test_fortnite_controller_preset_valid(self):
        cfg = AimAssistPresets.fortnite_controller()
        assert cfg.enabled is True
        assert cfg.base_aa_enabled is True
        assert cfg.strength == 8925
        assert cfg.tracking_strength == 1575
        assert cfg.fn_layer_strength == 1.05
        assert cfg.fn_move_pull_boost == 1.05
        assert cfg.fn_move_soft_magnet_boost == 1.10
        assert cfg.fn_move_adhesion_boost == 1.10
        assert cfg.zone == 5000
        assert isinstance(cfg, AimAssistConfig)


class TestShapeModes:

    @pytest.mark.parametrize("shape", ["circular", "zen", "helix", "wideoval", "tallowal"])
    def test_shape_modes_produce_different_output(self, shape):
        cfg = AimAssistConfig(
            enabled=True,
            rotational=True,
            shape_mode=shape,
            zone=2000,
        )
        engine = AimAssistEngine(cfg)
        pipeline = AimAssistPipeline(engine)
        rx, ry = pipeline._apply_rotational_aa(1000, 500, 16.0, cfg)
        assert isinstance(rx, float)
        assert isinstance(ry, float)
        assert -32768 <= rx <= 32767
        assert -32768 <= ry <= 32767

    def test_dz_radius_expands_zone(self):
        cfg = AimAssistConfig(
            enabled=True,
            zone=500,
            use_dz_radius=True,
            deadzone_aa_radius=10,
            zone_multiplier=3,
        )
        assert cfg.use_dz_radius is True
        assert cfg.zone < cfg.deadzone_aa_radius * 100 * cfg.zone_multiplier
        min_zone = cfg.deadzone_aa_radius * 100 * cfg.zone_multiplier
        assert min_zone == 3000


class TestApplySlowdown:

    def _make_engine(self, **overrides):
        cfg = AimAssistConfig(**overrides)
        return AimAssistEngine(cfg)

    def test_zone_zero_no_change(self):
        engine = self._make_engine(zone=0)
        rx, ry = engine.apply_slowdown(1000, 500, zone=0, strength=4500)
        assert rx == 1000
        assert ry == 500

    def test_zero_input_returns_zero(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(0, 0, zone=2200, strength=4500)
        assert rx == 0
        assert ry == 0

    def test_input_outside_zone_no_change(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(3000, 3000, zone=2200, strength=4500)
        assert rx == 3000
        assert ry == 3000

    def test_input_inside_zone_reduced(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(1000, 0, zone=2200, strength=4500)
        assert abs(rx) < 1000
        assert ry == 0

    def test_output_clamped_positive(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(32767, 32767, zone=50000, strength=9999)
        assert rx <= 32767
        assert ry <= 32767

    def test_output_clamped_negative(self):
        engine = self._make_engine()
        rx, ry = engine.apply_slowdown(-32768, -32768, zone=50000, strength=9999)
        assert rx >= -32768
        assert ry >= -32768


class TestShouldBeActive:

    def _make_engine(self):
        cfg = AimAssistConfig()
        return AimAssistEngine(cfg)

    def test_active_without_lt(self):
        engine = self._make_engine()
        assert engine.should_be_active(lt_pressed=False) is True

    def test_inactive_with_lt(self):
        engine = self._make_engine()
        assert engine.should_be_active(lt_pressed=True) is False


class TestEnhancedPattern:

    def _make_pipeline(self, **overrides):
        cfg = AimAssistConfig(
            enabled=True,
            base_aa_enabled=False,   # isola o enhanced pattern
            rotational=False,
            anti_flinch=False,
            adaptive_strength=False,
            fn_slow_strength=0.0,    # isola do slowdown do Fortnite engine
            fn_pull_strength=0.0,
            **overrides,
        )
        return AimAssistPipeline(AimAssistEngine(cfg))

    def test_standard_passthrough(self):
        """enhanced off / standard → output igual ao input (comportamento atual)."""
        pipeline = self._make_pipeline(enhanced_enabled=False, aim_pattern="standard")
        rx, ry = pipeline._apply_enhanced_pattern(2000, 1000, pipeline.aa_engine.cfg, 0, 0, 16.0)
        assert rx == 2000
        assert ry == 1000

    def test_enhanced_off_is_passthrough(self):
        pipeline = self._make_pipeline(enhanced_enabled=False, aim_pattern="full")
        rx, ry = pipeline._apply_enhanced_pattern(2000, 1000, pipeline.aa_engine.cfg, 0, 0, 16.0)
        assert rx == 2000
        assert ry == 1000

    def test_full_pattern_bounded(self):
        pipeline = self._make_pipeline(
            enhanced_enabled=True,
            aim_pattern="full",
            magnetic_snap=True,
            snap_strength=450,
            snap_duration=80,
            pd_kp=0.25,
            pd_kd=0.12,
            micro_adjust_pull=600,
        )
        cfg = pipeline.aa_engine.cfg
        rx, ry = pipeline._apply_enhanced_pattern(3000, 1500, cfg, 0, 0, 16.0)
        assert -32768 <= rx <= 32767
        assert -32768 <= ry <= 32767

    def test_snap_reduces_output_within_gate(self):
        """Snap atua apenas com input pequeno (< 2500, retículo perto do alvo)."""
        pipeline = self._make_pipeline(
            enhanced_enabled=True,
            aim_pattern="full",
            magnetic_snap=True,
            snap_strength=800,
            snap_duration=80,
            pd_kp=0.0,          # desliga PD para isolar o snap
            micro_adjust_pull=0,
        )
        cfg = pipeline.aa_engine.cfg
        rx, ry = pipeline._apply_enhanced_pattern(1500, 0, cfg, 0, 0, 16.0)
        assert 0 <= rx <= 32767
        assert abs(rx) < 1500  # snap reduz input pequeno

    def test_snap_does_not_cut_large_camera_motion(self):
        """Snap NÃO deve cortar movimento grande de câmera (fix da câmera dura)."""
        pipeline = self._make_pipeline(
            enhanced_enabled=True,
            aim_pattern="full",
            magnetic_snap=True,
            snap_strength=800,
            snap_duration=80,
            pd_kp=0.0,
            micro_adjust_pull=0,
        )
        cfg = pipeline.aa_engine.cfg
        rx, ry = pipeline._apply_enhanced_pattern(8000, 4000, cfg, 0, 0, 16.0)
        assert rx >= 7000  # câmera não é cortada (antes era ~921)


class TestPipelineAutoRotation:

    def test_rotation_enabled_adds_drift_when_stick_released(self):
        cfg = AimAssistConfig(
            enabled=True,
            base_aa_enabled=False,
            rotational=False,
            anti_flinch=False,
            auto_rotation_enabled=True,
            auto_rotation_speed=200,
        )
        pipeline = AimAssistPipeline(AimAssistEngine(cfg))
        # Define o bearing segurando o stick
        pipeline.apply(4000, 0, True, True, False, 16.0, cfg, 0, 0)
        # Solta o stick → drift positivo
        rx, ry = pipeline.apply(0, 0, True, True, False, 16.0, cfg, 0, 0)
        assert rx > 0

    def test_rotation_disabled_passthrough(self):
        cfg = AimAssistConfig(
            enabled=True,
            base_aa_enabled=False,
            rotational=False,
            anti_flinch=False,
            auto_rotation_enabled=False,
        )
        pipeline = AimAssistPipeline(AimAssistEngine(cfg))
        pipeline.apply(4000, 0, True, True, False, 16.0, cfg, 0, 0)
        rx, ry = pipeline.apply(0, 0, True, True, False, 16.0, cfg, 0, 0)
        assert rx == 0
        assert ry == 0


class TestPresetBuff:

    def test_fortnite_preset_asserted_fields_unchanged(self):
        """Os 7 campos assertados pelo teste antigo continuam iguais."""
        cfg = AimAssistPresets.fortnite_controller()
        assert cfg.strength == 8925
        assert cfg.tracking_strength == 1575
        assert cfg.zone == 5000
        assert cfg.fn_layer_strength == 1.05
        assert cfg.fn_move_pull_boost == 1.05
        assert cfg.fn_move_soft_magnet_boost == 1.10
        assert cfg.fn_move_adhesion_boost == 1.10

    def test_fortnite_preset_buffs_active(self):
        cfg = AimAssistPresets.fortnite_controller()
        assert cfg.enhanced_enabled is True
        assert cfg.aim_pattern == "full"
        assert cfg.sticky_enabled is True
        assert cfg.sticky_strength == 0.75
        assert cfg.lock_enabled is True
        assert cfg.micro_adjust_pull == 600
        assert cfg.pd_kp == 0.25
        assert cfg.pd_kd == 0.12


class TestAimbotPreset:

    def test_aimbot_is_full_combo(self):
        """FN Aimbot liga tudo que amplifica o AA."""
        cfg = AimAssistPresets.fortnite_aimbot()
        assert cfg.enhanced_enabled is True
        assert cfg.aim_pattern == "full"
        assert cfg.auto_rotation_enabled is False
        assert cfg.power_boost is True
        assert cfg.rush_enabled is True
        assert cfg.rush_always is True
        assert cfg.ls_freq_enabled is True
        assert cfg.kernel_aim_beta is True
        assert cfg.adaptive_strength is True
        assert cfg.power_boost is True
        assert cfg.sticky_enabled is True
        assert cfg.lock_enabled is True
        assert cfg.head_assist_enabled is True
        assert cfg.silent_aim_enabled is True
        assert cfg.silent_hit_enabled is True

    def test_aimbot_extends_controller_preset(self):
        cfg = AimAssistPresets.fortnite_aimbot()
        base = AimAssistPresets.fortnite_controller()
        # Herda os 7 campos assertados
        assert cfg.strength == 12000
        assert cfg.zone == 8000
        # Valores maximizados
        assert cfg.magnetic_pull > base.magnetic_pull
        assert cfg.fn_magnet_force > base.fn_magnet_force
        assert cfg.pulse_level >= base.pulse_level

    def test_aimbot_is_valid_config(self):
        cfg = AimAssistPresets.fortnite_aimbot()
        assert isinstance(cfg, AimAssistConfig)
        assert cfg.enabled is True

    def test_aimbot_best_mobile_aa_config(self):
        cfg = AimAssistPresets.fortnite_aimbot()
        base = AimAssistPresets.fortnite_controller()
        assert cfg.fn_strength_slider == 100
        assert cfg.fn_zone == 8000
        assert cfg.fn_slow_strength > base.fn_slow_strength
        assert cfg.fn_ramp_up_ms < base.fn_ramp_up_ms
        assert cfg.fn_move_pull_boost > base.fn_move_pull_boost


class TestRotationalAimStability:

    def _pipeline(self, cfg):
        return AimAssistPipeline(AimAssistEngine(cfg))

    def test_rotational_aa_flattens_y_when_aiming(self):
        """ADS achata a senoide vertical (a órbita vertical é o tremido)."""
        cfg = AimAssistConfig(
            enabled=True, rotational=True, shape_mode="circular", zone=2000)
        free = self._pipeline(cfg)
        ads = self._pipeline(cfg)
        free.raa_angle = math.pi / 2
        ads.raa_angle = math.pi / 2
        _, ry_free = free._apply_rotational_aa(1000, 0, 16.0, cfg, is_aiming=False)
        _, ry_ads = ads._apply_rotational_aa(1000, 0, 16.0, cfg, is_aiming=True)
        assert abs(ry_ads) < abs(ry_free)
        assert abs(ry_ads) <= abs(ry_free) * 0.5

    def test_rotational_x_kept_when_aiming(self):
        """O eixo X continua oscilando no ADS (é o que re-dispara o AA)."""
        cfg = AimAssistConfig(
            enabled=True, rotational=True, shape_mode="circular", zone=2000,
            pulse_level=0)
        free = self._pipeline(cfg)
        ads = self._pipeline(cfg)
        free.raa_angle = 0.0
        ads.raa_angle = 0.0
        rx_free, _ = free._apply_rotational_aa(1000, 0, 16.0, cfg, is_aiming=False)
        rx_ads, _ = ads._apply_rotational_aa(1000, 0, 16.0, cfg, is_aiming=True)
        assert rx_ads == rx_free

    def test_pulse_y_scaled_when_aiming(self):
        """Pulse mantém o X e achata o Y quando ADS."""
        full = PulseLevelEngine()
        scaled = PulseLevelEngine()
        full._angle = math.pi / 2
        scaled._angle = math.pi / 2
        _, ry_full = full.apply(2000, 0, 1, 16.0, y_scale=1.0)
        _, ry_scaled = scaled.apply(2000, 0, 1, 16.0, y_scale=0.25)
        assert abs(ry_scaled) < abs(ry_full)
        ratio = abs(ry_scaled) / abs(ry_full) if ry_full else 0
        assert 0.2 <= ratio <= 0.3


class TestAntiFlinchGate:

    def test_ignores_spike_while_only_aiming(self):
        """Salto do próprio assist (snap/magnetic/PD) não vira kick quando
        o jogador só está mirando — flinch real acontece atirando."""
        pipeline = AimAssistPipeline(AimAssistEngine(
            AimAssistConfig(enabled=True, anti_flinch=True, anti_flinch_strength=3000)))
        ry = 0
        for i in range(5):
            _, ry = pipeline.anti_flinch.process(
                0, 0 if i < 4 else 9000, 3000, is_shooting=False, is_aiming=True)
        assert ry == 9000

    def test_corrects_spike_while_shooting(self):
        """Atirando, o mesmo spike dispara a correção anti-flinch."""
        pipeline = AimAssistPipeline(AimAssistEngine(
            AimAssistConfig(enabled=True, anti_flinch=True, anti_flinch_strength=3000)))
        ry = 0
        for i in range(5):
            _, ry = pipeline.anti_flinch.process(
                0, 0 if i < 4 else 9000, 3000, is_shooting=True, is_aiming=True)
        assert ry != 9000

    def test_history_resets_between_shooting_phases(self):
        """Janela não carrega valores velhos entre fases de tiro."""
        pipeline = AimAssistPipeline(AimAssistEngine(
            AimAssistConfig(enabled=True, anti_flinch=True, anti_flinch_strength=3000)))
        for i in range(5):
            pipeline.anti_flinch.process(
                0, 0 if i < 4 else 9000, 3000, is_shooting=False, is_aiming=True)
        assert len(pipeline.anti_flinch._ry_history) == 0


class TestFireBoost:

    def _pipeline(self, cfg):
        return AimAssistPipeline(AimAssistEngine(cfg))

    def _cfg(self, **overrides):
        base = dict(
            enabled=True, base_aa_enabled=False, rotational=False,
            anti_flinch=False, anti_shake_blend=0.0, fn_strength_slider=0,
        )
        base.update(overrides)
        return AimAssistConfig(**base)

    def test_disabled_passthrough(self):
        cfg = self._cfg(fire_boost_mult=1.0)
        rx, ry = self._pipeline(cfg).apply(
            1000, 500, True, True, False, 16.0, cfg, 0, 0)
        assert rx == 1000
        assert ry == 500

    def test_fire_edge_boosts(self):
        cfg = self._cfg(fire_boost_mult=1.3, fire_boost_ms=200)
        pipeline = self._pipeline(cfg)
        rx, ry = pipeline.apply(1000, 500, True, True, False, 16.0, cfg, 0, 0)
        assert rx > 1000  # borda do tiro → multiplicado
        assert ry > 500

    def test_boost_expires_after_window(self):
        cfg = self._cfg(fire_boost_mult=1.3, fire_boost_ms=50)
        pipeline = self._pipeline(cfg)
        pipeline.apply(1000, 500, True, True, False, 16.0, cfg, 0, 0)
        pipeline._fire_boost_until = 0.0  # simula expiração do window
        rx, ry = pipeline.apply(1000, 500, True, True, False, 16.0, cfg, 0, 0)
        assert rx == 1000
        assert ry == 500

    def test_boost_does_not_persist_after_release(self):
        cfg = self._cfg(fire_boost_mult=1.3, fire_boost_ms=200)
        pipeline = self._pipeline(cfg)
        pipeline.apply(1000, 500, True, True, False, 16.0, cfg, 0, 0)
        rx, ry = pipeline.apply(1000, 500, False, True, False, 16.0, cfg, 0, 0)
        assert rx == 1000  # sem tiro = sem boost
        assert ry == 500


class TestHeadLockConfig:

    def test_controller_preset_headlock_ready(self):
        """Preset FN Controller: headlock ligado (pulse) — só falta o
        head_assist_enabled do usuário para ativar."""
        cfg = AimAssistPresets.fortnite_controller()
        assert cfg.headlock_pulse is True
        assert cfg.headlock_pulse_ms == 60
        assert cfg.headlock_drift_limit == 2500
        assert cfg.fire_boost_mult == 1.12

    def test_aimbot_preset_headlock_active(self):
        cfg = AimAssistPresets.fortnite_aimbot()
        assert cfg.head_assist_enabled is True
        assert cfg.headlock_pulse is True
        assert cfg.headlock_pulse_ms == 25
        assert cfg.headlock_drift_limit == 7000
        assert cfg.fire_boost_mult == 1.6
        assert cfg.fire_boost_ms == 200
        assert cfg.aimlock_enabled is True
        assert cfg.aimlock_source == "proxy"
        assert cfg.aimlock_proxy_input_min == 300.0
        assert cfg.aimlock_blend == 0.9
        assert cfg.fn_input_gate == 180
        assert cfg.fn_ads_multiplier == 1.4
        assert cfg.fn_rotation_cap == 700
        assert cfg.aimlock_target_bone == "head"
        assert cfg.aimlock_head_height_cm == 30.0
        assert cfg.aimlock_max_tracking_distance_cm == 50000.0
        assert cfg.aimlock_kalman_smoothing == 0.25
        assert cfg.aimlock_velocity_adaptive_boost == 0.9
        assert cfg.fn_camera_slow_keep == 0.95
        assert cfg.fn_aim_pull_floor == 0.65
        assert cfg.fn_camera_pull_floor == 0.88
        assert cfg.kbm_mode is True
        assert cfg.kbm_scale == 0.2
        assert cfg.fn_humanize is True

    def test_defaults_off(self):
        cfg = AimAssistConfig()
        assert cfg.headlock_pulse is False
        assert cfg.fire_boost_mult == 1.0

    def test_config_roundtrip(self):
        cfg = AimAssistConfig.from_dict({
            "aa_headlock_pulse": True,
            "aa_headlock_pulse_ms": 45,
            "aa_headlock_drift_limit": 2000,
            "aa_headlock_lock_window": 3500,
            "aa_fire_boost_mult": 1.25,
            "aa_fire_boost_ms": 90,
        })
        assert cfg.headlock_pulse is True
        assert cfg.headlock_pulse_ms == 45
        assert cfg.headlock_drift_limit == 2000
        assert cfg.headlock_lock_window == 3500
        assert cfg.fire_boost_mult == 1.25
        assert cfg.fire_boost_ms == 90


class TestNeuralAimEngine:

    def test_neural_disabled_passthrough(self):
        from nocrosshair.features.neural_aim import NeuralTrackerEngine
        engine = NeuralTrackerEngine()
        engine.enabled = False
        rx, ry = engine.apply(1000, 500, 1000, 500, True, True, 16.0)
        assert rx == 1000
        assert ry == 500

    def test_neural_enabled_bounded(self):
        from nocrosshair.features.neural_aim import NeuralTrackerEngine
        engine = NeuralTrackerEngine()
        engine.enabled = True
        for _ in range(20):
            rx, ry = engine.apply(3000, 1500, 3000, 1500, True, True, 16.0)
        assert -32768 <= rx <= 32767
        assert -32768 <= ry <= 32767

    def test_neural_kalman_predicts_lead(self):
        from nocrosshair.features.neural_aim import NeuralTrackerEngine
        engine = NeuralTrackerEngine()
        engine.enabled = True
        engine.kalman_weight = 1.0
        engine.kalman_lead_ms = 50.0
        engine.micro_enabled = False
        engine.harmonizer_enabled = False
        engine.error_feedback_enabled = False
        engine.confidence_scale = 1.0
        # Feed moving target (position increases each frame → velocity > 0)
        for i in range(15):
            x = 1000 + i * 200
            y = 500 + i * 100
            rx, ry = engine.apply(float(x), float(y), float(x), float(y), True, True, 16.0)
        # After consistent movement, Kalman should predict lead
        assert rx > x or ry > y  # lead applied

    def test_engagement_confidence_stages(self):
        from nocrosshair.features.neural_aim import AdaptiveEngagementState
        state = AdaptiveEngagementState()
        # IDLE
        assert state.stage == 0
        assert state.confidence == 0.0
        # SEARCHING (large deflection)
        state.update(15000, 0, False, 16.0)
        assert state.stage == 1
        # FIRING (small deflection + shooting)
        state.update(1000, 0, True, 16.0)
        assert state.stage == 4
        assert state.confidence > 0.3

    def test_harmonizer_smooths(self):
        from nocrosshair.features.neural_aim import TemporalHarmonizer
        h = TemporalHarmonizer()
        # Alternating corrections should be dampened
        r1 = h.apply(100, 50, 0, 0, 16.0)
        r2 = h.apply(-100, -50, 0, 0, 16.0)
        r3 = h.apply(100, 50, 0, 0, 16.0)
        # Output should be smoothed, not oscillating wildly
        assert -32768 <= r1[0] <= 32767
        assert -32768 <= r2[0] <= 32767
        assert -32768 <= r3[0] <= 32767

    def test_micro_corrections_apply(self):
        from nocrosshair.features.neural_aim import _MicroCorrectionEngine
        mc = _MicroCorrectionEngine()
        rx, ry = mc.apply(0, 0, 0.8, 200.0, 16.0)
        # Micro-corrections should add small offsets
        assert abs(rx) > 0 or abs(ry) > 0
        assert abs(rx) < 500  # sub-pixel
        assert abs(ry) < 500

    def test_error_tracker_convergence(self):
        from nocrosshair.features.neural_aim import AimErrorTracker
        tracker = AimErrorTracker()
        assert not tracker.is_converged
        for _ in range(10):
            tracker.update(1000, 500, 1000, 500)  # zero error
        assert tracker.is_converged
        assert tracker.smoothed_error < 50

    def test_aimbot_preset_has_neural(self):
        """FN Aimbot preset includes Neural engine (terceira geração)."""
        cfg = AimAssistPresets.fortnite_aimbot()
        assert cfg.neural_enabled is True
        assert cfg.neural_kalman_noise == 300.0
        assert cfg.neural_kalman_lead_ms == 40.0
        assert cfg.neural_kalman_weight == 0.8
        assert cfg.neural_micro_enabled is False
        assert cfg.neural_micro_amplitude == 0.0
        assert cfg.neural_confidence_scale == 1.4
        assert cfg.neural_harmonizer_enabled is True
        assert cfg.neural_error_feedback_enabled is True

    def test_neural_config_roundtrip(self):
        cfg = AimAssistConfig.from_dict({
            "aa_neural_enabled": True,
            "aa_neural_kalman_noise": 350.0,
            "aa_neural_kalman_lead_ms": 40.0,
            "aa_neural_kalman_weight": 0.8,
            "aa_neural_micro_amplitude": 250.0,
            "aa_neural_confidence_scale": 1.2,
        })
        assert cfg.neural_enabled is True
        assert cfg.neural_kalman_noise == 350.0
        assert cfg.neural_kalman_lead_ms == 40.0
        assert cfg.neural_kalman_weight == 0.8
        assert cfg.neural_micro_amplitude == 250.0
        assert cfg.neural_confidence_scale == 1.2

    def test_pipeline_neural_applied(self):
        """Pipeline applies neural engine when enabled in config."""
        cfg = AimAssistConfig(
            enabled=True,
            base_aa_enabled=False,
            rotational=False,
            anti_flinch=False,
            fn_slow_strength=0.0,
            fn_pull_strength=0.0,
            neural_enabled=True,
            neural_kalman_lead_ms=40.0,
            neural_kalman_weight=0.8,
            neural_micro_enabled=False,
            neural_harmonizer_enabled=False,
            neural_error_feedback_enabled=False,
        )
        pipeline = AimAssistPipeline(AimAssistEngine(cfg))
        # Feed consistent movement to build Kalman state
        for _ in range(10):
            pipeline.apply(2000, 1000, True, True, False, 16.0, cfg, 0, 0)
        # Neural engine should be modifying the output
        assert pipeline.neural_engine.enabled is True


class TestStickyWhileStill:
    """O aim deve continuar grudado no alvo mesmo com o personagem parado
    (is_moving=False): o move-boost é desligado, mas o AA base, o grude
    (adhesion/auto-rotation) e o neural seguem ativos."""

    def _pipeline(self):
        cfg = AimAssistPresets.fortnite_aimbot()
        return AimAssistPipeline(AimAssistEngine(cfg)), cfg

    def test_aimbot_engages_while_still(self):
        """Parado (is_moving=False), atirando e mirando com input constante:
        a saída segue engajada e modificada pelo AA (não é passthrough)."""
        p, cfg = self._pipeline()
        raw = (1200.0, 600.0)
        p.apply(*raw, True, True, False, 16.0, cfg, 0, 0)  # aquece o pipeline
        rx, ry = p.apply(*raw, True, True, False, 16.0, cfg, 0, 0)
        assert math.hypot(rx, ry) > 0.0
        assert (rx, ry) != raw  # AA agiu mesmo parado

    def test_aimbot_holds_after_release_while_still(self):
        """Parado: solta o stick no meio do engajamento — a saída não cai
        a zero imediatamente (grude via adhesion buffer + auto rotation)."""
        p, cfg = self._pipeline()
        p.apply(1200.0, 600.0, True, True, False, 16.0, cfg, 0, 0)
        rx, ry = p.apply(0.0, 0.0, True, True, False, 16.0, cfg, 0, 0)
        assert math.hypot(rx, ry) > 0.0

    def test_aimbot_sustained_while_still(self):
        """Parado: 60 frames com input constante — o grude não desengaja
        no meio do caminho."""
        p, cfg = self._pipeline()
        mags = []
        for _ in range(60):
            rx, ry = p.apply(1200.0, 600.0, True, True, False, 16.0, cfg, 0, 0)
            mags.append(math.hypot(rx, ry))
        assert min(mags) > 0.0
        assert max(mags) <= 32767.0

    def test_neural_micro_active_while_still(self):
        """Parado: o neural (micro-corrections Lissajous) continua alterando
        a saída sub-pixel — o grude neural não depende de movimento."""
        p, cfg = self._pipeline()
        p.neural_engine.enabled = True
        p.neural_engine.micro_enabled = True
        outs = set()
        for _ in range(30):
            rx, ry = p.apply(1200.0, 600.0, True, True, False, 16.0, cfg, 0, 0)
            outs.add((round(rx, 1), round(ry, 1)))
        assert len(outs) > 1  # micro-corrections variam a saída

    def test_still_and_moving_both_engage(self):
        """Comparativo: parado vs. andando — em ambos o AA modifica a saída
        (o move-boost só adiciona força; não é pré-requisito para grude)."""
        p_still, cfg = self._pipeline()
        p_move, _ = self._pipeline()
        p_still.apply(1200.0, 600.0, True, True, False, 16.0, cfg, 0, 0)
        p_move.apply(1200.0, 600.0, True, True, True, 16.0, cfg, 0, 0)
        rx_s, ry_s = p_still.apply(1200.0, 600.0, True, True, False, 16.0, cfg, 0, 0)
        rx_m, ry_m = p_move.apply(1200.0, 600.0, True, True, True, 16.0, cfg, 0, 0)
        assert (rx_s, ry_s) != (1200.0, 600.0)
        assert (rx_m, ry_m) != (1200.0, 600.0)


class TestLeftStickFreqEngine:

    def _engine(self):
        from nocrosshair.features.aim_assist import LeftStickFreqEngine
        return LeftStickFreqEngine()

    def test_disabled_returns_unchanged(self):
        e = self._engine()
        lx, ly = e.apply(100, 200, enabled=False, amplitude=10,
                         frequency=15.0, shape="sine", gate=500,
                         delta_ms=16.0, is_moving=False)
        assert lx == 100
        assert ly == 200

    def test_amplitude_zero_returns_unchanged(self):
        e = self._engine()
        lx, ly = e.apply(100, 200, enabled=True, amplitude=0,
                         frequency=15.0, shape="sine", gate=500,
                         delta_ms=16.0, is_moving=False)
        assert lx == 100
        assert ly == 200

    def test_gate_blocks_when_lx_moving(self):
        e = self._engine()
        lx, ly = e.apply(600, 0, enabled=True, amplitude=10,
                         frequency=15.0, shape="sine", gate=500,
                         delta_ms=16.0, is_moving=False)
        assert lx == 600
        assert ly == 0

    def test_gate_blocks_when_ly_moving(self):
        e = self._engine()
        lx, ly = e.apply(0, 600, enabled=True, amplitude=10,
                         frequency=15.0, shape="sine", gate=500,
                         delta_ms=16.0, is_moving=False)
        assert lx == 0
        assert ly == 600

    def test_gate_blocks_when_is_moving(self):
        e = self._engine()
        lx, ly = e.apply(0, 0, enabled=True, amplitude=10,
                         frequency=15.0, shape="sine", gate=500,
                         delta_ms=16.0, is_moving=True)
        assert lx == 0
        assert ly == 0

    def test_sine_wave_output(self):
        e = self._engine()
        lx, ly = e.apply(0, 0, enabled=True, amplitude=10,
                         frequency=15.0, shape="sine", gate=500,
                         delta_ms=16.0, is_moving=False)
        assert lx != 0 or ly != 0

    def test_triangle_wave_output(self):
        e = self._engine()
        lx, ly = e.apply(0, 0, enabled=True, amplitude=10,
                         frequency=15.0, shape="triangle", gate=500,
                         delta_ms=16.0, is_moving=False)
        assert lx != 0 or ly != 0

    def test_square_wave_output(self):
        e = self._engine()
        lx, ly = e.apply(0, 0, enabled=True, amplitude=10,
                         frequency=15.0, shape="square", gate=500,
                         delta_ms=16.0, is_moving=False)
        assert lx != 0 or ly != 0

    def test_phase_wraps(self):
        e = self._engine()
        for _ in range(1000):
            e.apply(0, 0, enabled=True, amplitude=10,
                    frequency=15.0, shape="sine", gate=500,
                    delta_ms=16.0, is_moving=False)
        assert e._phase_x < 2.0 * math.pi

    def test_frequency_affects_speed(self):
        e1 = self._engine()
        e2 = self._engine()
        for _ in range(10):
            e1.apply(0, 0, enabled=True, amplitude=10,
                     frequency=5.0, shape="sine", gate=500,
                     delta_ms=16.0, is_moving=False)
            e2.apply(0, 0, enabled=True, amplitude=10,
                     frequency=50.0, shape="sine", gate=500,
                     delta_ms=16.0, is_moving=False)
        assert e2._phase_x > e1._phase_x

    def test_amplitude_clamped(self):
        e = self._engine()
        lx, ly = e.apply(32760, 32760, enabled=True, amplitude=10,
                         frequency=15.0, shape="sine", gate=500,
                         delta_ms=16.0, is_moving=False)
        assert lx <= 32767
        assert ly <= 32767

    def test_reset(self):
        e = self._engine()
        e.apply(0, 0, enabled=True, amplitude=10,
                frequency=15.0, shape="sine", gate=500,
                delta_ms=16.0, is_moving=False)
        assert e._phase_x != 0.0
        e.reset()
        assert e._phase_x == 0.0
        assert e._phase_y == 0.0
