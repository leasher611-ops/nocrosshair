"""Reproduz o bug: camera drift com input zero e aim habilitado."""
import math, time
from nocrosshair.features.aim_assist import AimAssistPresets, AimAssistPipeline, AimAssistEngine

def test_zero_input_produces_zero_output():
    """Com TODAS as funções desligadas mas aim_master=True, output deve ser 0."""
    cfg = AimAssistPresets.fortnite_aimbot()
    # Desliga tudo exceto aim_master (enabled)
    for attr in [
        "sticky_enabled", "lock_enabled", "head_assist_enabled",
        "base_aa_enabled", "auto_rotation_enabled", "enhanced_enabled",
        "adaptive_strength", "rotational", "aimlock_enabled",
        "anti_recoil_ml_enabled", "ballistic_predictor_enabled",
        "smart_headshot_enabled", "neural_enabled", "neural_micro_enabled",
        "oef_enabled", "adhesion_buffer_enabled", "predictive_tracker_enabled",
        "follow_assist_enabled", "anti_flinch", "magnetic_pull",
    ]:
        if attr == "magnetic_pull":
            setattr(cfg, attr, 0)
        else:
            setattr(cfg, attr, False)
    cfg.fire_boost_mult = 1.0
    cfg.anti_shake_blend = 0.0
    cfg.tracking = False
    cfg.auto_track_enabled = False

    assert cfg.enabled, "aim_master deve estar True"

    pipe = AimAssistPipeline(AimAssistEngine(cfg))
    # Hold
    for i in range(40):
        pipe.apply(2000.0, 800.0, True, True, False, 1.0, cfg, 2000.0, 800.0)
    # Release - esperado: output = 0
    drift_mags = []
    for i in range(200):
        rx, ry = pipe.apply(0.0, 0.0, True, True, False, 1.0, cfg, 0.0, 0.0)
        drift_mags.append(math.hypot(rx, ry))
    
    max_drift = max(drift_mags)
    final_drift = drift_mags[-1]
    print(f"  aim_master=ON, all features OFF:")
    print(f"    max_drift={max_drift:.0f} final_drift={final_drift:.0f}")
    if max_drift > 10:
        print(f"    *** BUG: camera drift detectado! max={max_drift:.0f}")
    else:
        print(f"    OK: sem drift")
    return max_drift

def test_with_base_aa_only():
    """Só base_aa habilitado."""
    cfg = AimAssistPresets.fortnite_aimbot()
    for attr in [
        "sticky_enabled", "lock_enabled", "head_assist_enabled",
        "auto_rotation_enabled", "enhanced_enabled",
        "adaptive_strength", "rotational", "aimlock_enabled",
        "anti_recoil_ml_enabled", "ballistic_predictor_enabled",
        "smart_headshot_enabled", "neural_enabled", "neural_micro_enabled",
        "oef_enabled", "adhesion_buffer_enabled", "predictive_tracker_enabled",
        "follow_assist_enabled", "anti_flinch", "magnetic_pull",
    ]:
        if attr == "magnetic_pull":
            setattr(cfg, attr, 0)
        else:
            setattr(cfg, attr, False)
    cfg.fire_boost_mult = 1.0
    cfg.anti_shake_blend = 0.0
    cfg.tracking = False
    cfg.auto_track_enabled = False

    pipe = AimAssistPipeline(AimAssistEngine(cfg))
    for i in range(40):
        pipe.apply(2000.0, 800.0, True, True, False, 1.0, cfg, 2000.0, 800.0)
    drift_mags = []
    for i in range(200):
        rx, ry = pipe.apply(0.0, 0.0, True, True, False, 1.0, cfg, 0.0, 0.0)
        drift_mags.append(math.hypot(rx, ry))
    
    max_drift = max(drift_mags)
    print(f"  base_aa only:")
    print(f"    max_drift={max_drift:.0f} final={drift_mags[-1]:.0f}")
    return max_drift

def test_with_sticky_only():
    cfg = AimAssistPresets.fortnite_aimbot()
    for attr in [
        "base_aa_enabled", "lock_enabled", "head_assist_enabled",
        "auto_rotation_enabled", "enhanced_enabled",
        "adaptive_strength", "rotational", "aimlock_enabled",
        "anti_recoil_ml_enabled", "ballistic_predictor_enabled",
        "smart_headshot_enabled", "neural_enabled", "neural_micro_enabled",
        "oef_enabled", "adhesion_buffer_enabled", "predictive_tracker_enabled",
        "follow_assist_enabled", "anti_flinch", "magnetic_pull",
    ]:
        if attr == "magnetic_pull":
            setattr(cfg, attr, 0)
        else:
            setattr(cfg, attr, False)
    cfg.fire_boost_mult = 1.0
    cfg.anti_shake_blend = 0.0

    pipe = AimAssistPipeline(AimAssistEngine(cfg))
    for i in range(40):
        pipe.apply(2000.0, 800.0, True, True, False, 1.0, cfg, 2000.0, 800.0)
    drift_mags = []
    for i in range(200):
        rx, ry = pipe.apply(0.0, 0.0, True, True, False, 1.0, cfg, 0.0, 0.0)
        drift_mags.append(math.hypot(rx, ry))
    
    max_drift = max(drift_mags)
    print(f"  sticky only:")
    print(f"    max_drift={max_drift:.0f} final={drift_mags[-1]:.0f}")
    return max_drift

def test_with_lock_only():
    cfg = AimAssistPresets.fortnite_aimbot()
    for attr in [
        "base_aa_enabled", "sticky_enabled", "head_assist_enabled",
        "auto_rotation_enabled", "enhanced_enabled",
        "adaptive_strength", "rotational", "aimlock_enabled",
        "anti_recoil_ml_enabled", "ballistic_predictor_enabled",
        "smart_headshot_enabled", "neural_enabled", "neural_micro_enabled",
        "oef_enabled", "adhesion_buffer_enabled", "predictive_tracker_enabled",
        "follow_assist_enabled", "anti_flinch", "magnetic_pull",
    ]:
        if attr == "magnetic_pull":
            setattr(cfg, attr, 0)
        else:
            setattr(cfg, attr, False)
    cfg.fire_boost_mult = 1.0
    cfg.anti_shake_blend = 0.0

    pipe = AimAssistPipeline(AimAssistEngine(cfg))
    for i in range(40):
        pipe.apply(2000.0, 800.0, True, True, False, 1.0, cfg, 2000.0, 800.0)
    drift_mags = []
    for i in range(200):
        rx, ry = pipe.apply(0.0, 0.0, True, True, False, 1.0, cfg, 0.0, 0.0)
        drift_mags.append(math.hypot(rx, ry))
    
    max_drift = max(drift_mags)
    print(f"  lock only:")
    print(f"    max_drift={max_drift:.0f} final={drift_mags[-1]:.0f}")
    return max_drift

print("=== Reprodução do bug: camera drift com input zero ===\n")
d1 = test_zero_input_produces_zero_output()
d2 = test_with_base_aa_only()
d3 = test_with_sticky_only()
d4 = test_with_lock_only()

print(f"\nResumo: all_off={d1:.0f} base_aa={d2:.0f} sticky={d3:.0f} lock={d4:.0f}")
if d1 > 10:
    print("*** BUG CONFIRMADO: pipeline produz output com input zero!")
