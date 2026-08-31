#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Neural-level aim assist engine (third generation).

Three orthogonal engines that push aim assist beyond the current state of art:

1. :class:`NeuralTrackerEngine` — Kalman filter trajectory predictor with
   state-space model (position + velocity), confidence-gated corrections,
   and micro-correction injection at multiple frequencies. Replaces the
   simple alpha-beta predict with a proper Bayesian estimator.

2. :class:`AdaptiveEngagementState` — Multi-stage engagement detector that
   tracks how long the player has been on-target and dynamically scales
   assistance strength. Combines velocity coherence, directional stability,
   and temporal dwell into a single confidence score.

3. :class:`TemporalHarmonizer` — Cross-layer temporal smoothing that prevents
   overcorrection between engines (PD controller fighting with snap, for
   example), and injects human-like timing jitter so corrections don't
   repeat at a fixed rate (which would be detected as non-human input).

All engines are additive and composable. They don't replace existing engines
but sit on top, providing a higher-level "neural" layer of correction.
"""

import math
import time
import random
from typing import Tuple, Optional, List
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────────────
# Kalman Filter (2D position + velocity state-space model)
# ──────────────────────────────────────────────────────────────────────

class _Kalman2D:
    """Minimal 2D Kalman filter for position tracking with velocity estimation.

    State vector: [x, y, vx, vy]
    Measurement:  [x, y]
    Predicts position ahead by t ms for lead computation.
    """

    def __init__(self) -> None:
        # State: [x, y, vx, vy]
        self._x = [0.0, 0.0, 0.0, 0.0]
        # State covariance (4x4, flattened row-major)
        self._P = [
            1000.0, 0.0, 0.0, 0.0,
            0.0, 1000.0, 0.0, 0.0,
            0.0, 0.0, 1000.0, 0.0,
            0.0, 0.0, 0.0, 1000.0,
        ]
        self._initialized = False

    def predict(self, dt: float) -> None:
        """Predict state forward by dt seconds."""
        dt = max(dt, 1e-6)
        # F = identity + dt * velocity coupling
        # x' = x + vx*dt, y' = y + vy*dt, vx'=vx, vy'=vy
        self._x[0] += self._x[2] * dt
        self._x[1] += self._x[3] * dt
        # P' = F * P * F^T + Q
        # Simplified: velocity uncertainty grows with dt
        q_v = 100.0 * dt  # process noise per velocity component
        self._P[0] += 2.0 * dt * self._P[2] + dt * dt * self._P[10]
        self._P[5] += 2.0 * dt * self._P[7] + dt * dt * self._P[15]
        self._P[10] += q_v
        self._P[15] += q_v
        self._P[2] += dt * self._P[10]
        self._P[7] += dt * self._P[15]

    def update(self, z_x: float, z_y: float, measurement_noise: float) -> None:
        """Incorporate measurement [z_x, z_y] with given noise variance."""
        if not self._initialized:
            self._x[0] = z_x
            self._x[1] = z_y
            self._x[2] = 0.0
            self._x[3] = 0.0
            self._initialized = True
            return

        # Innovation
        inn_x = z_x - self._x[0]
        inn_y = z_y - self._x[1]
        R = measurement_noise

        # S = H * P * H^T + R  (H selects position components)
        S_x = self._P[0] + R
        S_y = self._P[5] + R

        # K = P * H^T * S^-1
        K = [0.0] * 4
        K[0] = self._P[0] / S_x
        K[1] = self._P[5] / S_y
        K[2] = self._P[2] / S_x
        K[3] = self._P[7] / S_y

        # Update state
        self._x[0] += K[0] * inn_x
        self._x[1] += K[1] * inn_y
        self._x[2] += K[2] * inn_x
        self._x[3] += K[3] * inn_y

        # Update covariance
        ik00 = 1.0 - K[0]
        ik11 = 1.0 - K[1]
        self._P[0] = ik00 * self._P[0]
        self._P[5] = ik11 * self._P[5]
        self._P[2] = ik00 * self._P[2]
        self._P[7] = ik11 * self._P[7]

    def predict_lead(self, lead_ms: float) -> Tuple[float, float]:
        """Return predicted position lead in (x, y) from current estimate."""
        t = lead_ms / 1000.0
        lead_x = self._x[2] * t
        lead_y = self._x[3] * t
        return lead_x, lead_y

    @property
    def velocity(self) -> Tuple[float, float]:
        return self._x[2], self._x[3]

    @property
    def speed(self) -> float:
        return math.hypot(self._x[2], self._x[3])

    def reset(self) -> None:
        self._x = [0.0, 0.0, 0.0, 0.0]
        self._P = [
            1000.0, 0.0, 0.0, 0.0,
            0.0, 1000.0, 0.0, 0.0,
            0.0, 0.0, 1000.0, 0.0,
            0.0, 0.0, 0.0, 1000.0,
        ]
        self._initialized = False


# ──────────────────────────────────────────────────────────────────────
# Micro-Correction Engine (multi-frequency sub-pixel corrections)
# ──────────────────────────────────────────────────────────────────────

class _MicroCorrectionEngine:
    """Injects sub-pixel corrections at multiple natural frequencies.

    Uses a Lissajous pattern (ratio of two prime-number frequencies)
    to create organic-looking correction orbits that don't repeat at
    a detectable fixed rate. Amplitude scales with engagement confidence.
    """

    def __init__(self) -> None:
        self._phase_x: float = 0.0
        self._phase_y: float = 0.0
        # Two coprime frequencies for Lissajous pattern
        self._freq_x: float = 7.3  # ~7.3 Hz base
        self._freq_y: float = 5.1  # ~5.1 Hz (coprime ratio → non-repeating)
        self._harmonic_strength: float = 0.15  # 2nd harmonic amplitude ratio

    def apply(self, rx: float, ry: float, confidence: float,
              amplitude: float, delta_ms: float,
              humanize: bool = True) -> Tuple[float, float]:
        """Apply multi-frequency micro-corrections.

        - confidence: 0.0–1.0 engagement confidence → scales amplitude
        - amplitude: max micro-correction magnitude (stick units)
        - humanize: if True, adds slight frequency modulation for organic feel
        """
        if confidence <= 0.05 or amplitude <= 0.0:
            return rx, ry

        dt = delta_ms / 1000.0
        self._phase_x += 2.0 * math.pi * self._freq_x * dt
        self._phase_y += 2.0 * math.pi * self._freq_y * dt

        # Wrap phases
        if self._phase_x > 2.0 * math.pi:
            self._phase_x -= 2.0 * math.pi
        if self._phase_y > 2.0 * math.pi:
            self._phase_y -= 2.0 * math.pi

        # Lissajous with 2nd harmonic for organic shape
        base_x = math.sin(self._phase_x)
        base_y = math.sin(self._phase_y)
        harm_x = self._harmonic_strength * math.sin(self._phase_x * 2.0 + 0.7)
        harm_y = self._harmonic_strength * math.sin(self._phase_y * 2.0 + 1.1)

        micro_x = (base_x + harm_x) * amplitude * confidence
        micro_y = (base_y + harm_y) * amplitude * confidence

        if humanize:
            # Slow frequency modulation (0.1–0.3 Hz range)
            drift = math.sin(self._phase_x * 0.02) * 0.12
            micro_x *= (1.0 + drift)
            micro_y *= (1.0 - drift * 0.5)

        return max(-32767.0, min(32767.0, rx + micro_x)), \
               max(-32767.0, min(32767.0, ry + micro_y))

    def reset(self) -> None:
        self._phase_x = 0.0
        self._phase_y = 0.0


# ──────────────────────────────────────────────────────────────────────
# Engagement Confidence System
# ──────────────────────────────────────────────────────────────────────

class AdaptiveEngagementState:
    """Multi-stage engagement detector with confidence scoring.

    Stages:
      0. IDLE       — no meaningful input or not shooting
      1. SEARCHING  — moving stick, looking for target
      2. APPROACH   — stick deflection decreasing (proximity to target)
      3. LOCKED     — low deflection + sustained → high confidence
      4. FIRING     — locked + shooting → maximum confidence

    The confidence score (0.0–1.0) is the product of:
      - velocity coherence: consistent direction over time
      - directional stability: low variance in stick angle
      - temporal dwell: how long in LOCKED/FIRING stage
    """

    IDLE = 0
    SEARCHING = 1
    APPROACH = 2
    LOCKED = 3
    FIRING = 4

    def __init__(self) -> None:
        self.stage: int = self.IDLE
        self.confidence: float = 0.0
        self._stage_start: float = 0.0
        self._direction_history: List[float] = []
        self._max_history: int = 12
        self._lock_dwell_ms: float = 0.0
        self._prev_mag: float = 0.0
        self._velocity_coherence: float = 0.0
        self._directional_stability: float = 0.0

    def update(self, rx: float, ry: float, is_shooting: bool,
               delta_ms: float) -> None:
        """Update engagement state from current right stick input."""
        now = time.monotonic()
        mag = math.hypot(rx, ry)

        # Track direction history for coherence/stability
        if mag > 100:
            angle = math.atan2(ry, rx)
            self._direction_history.append(angle)
            if len(self._direction_history) > self._max_history:
                self._direction_history.pop(0)
        elif len(self._direction_history) > 4:
            # Decay history when stick is idle
            self._direction_history = self._direction_history[-4:]

        # Compute velocity coherence (how consistent is the direction)
        self._velocity_coherence = self._compute_coherence()
        self._directional_stability = self._compute_stability()

        # Stage detection
        if mag < 30:
            new_stage = self.IDLE
        elif mag > 8000:
            new_stage = self.SEARCHING
        elif mag < 2500 and not is_shooting:
            new_stage = self.APPROACH
        elif mag < 2500 and is_shooting:
            new_stage = self.FIRING
        else:
            new_stage = self.LOCKED if is_shooting else self.APPROACH

        if new_stage != self.stage:
            self._stage_start = now
            self.stage = new_stage

        # Dwell time
        if self.stage >= self.LOCKED:
            self._lock_dwell_ms += delta_ms
        else:
            self._lock_dwell_ms = max(0.0, self._lock_dwell_ms - delta_ms * 0.5)

        # Compute confidence
        self.confidence = self._compute_confidence(delta_ms)
        self._prev_mag = mag

    def _compute_coherence(self) -> float:
        """Measure how consistent the input direction is (0–1)."""
        if len(self._direction_history) < 3:
            return 0.5
        # Circular variance of recent angles
        mean_cos = sum(math.cos(a) for a in self._direction_history) / len(self._direction_history)
        mean_sin = sum(math.sin(a) for a in self._direction_history) / len(self._direction_history)
        r = math.hypot(mean_cos, mean_sin)  # 1 = perfectly coherent, 0 = random
        return max(0.0, min(1.0, r))

    def _compute_stability(self) -> float:
        """Measure how stable the input magnitude is (0–1)."""
        if len(self._direction_history) < 3:
            return 0.5
        # Use angular variance as stability proxy
        coherence = self._velocity_coherence
        return coherence  # Coherent direction → stable

    def _compute_confidence(self, delta_ms: float) -> float:
        """Combine all factors into a single confidence score."""
        # Base: stage-dependent
        stage_base = {
            self.IDLE: 0.0,
            self.SEARCHING: 0.05,
            self.APPROACH: 0.25,
            self.LOCKED: 0.55,
            self.FIRING: 0.70,
        }.get(self.stage, 0.0)

        # Velocity coherence bonus (up to +0.15)
        coherence_bonus = self._velocity_coherence * 0.15

        # Directional stability bonus (up to +0.10)
        stability_bonus = self._directional_stability * 0.10

        # Temporal dwell bonus (ramps up over 200ms, max +0.10)
        dwell_bonus = min(0.10, self._lock_dwell_ms / 2000.0)

        # Decay of previous confidence (smooth transitions)
        raw = stage_base + coherence_bonus + stability_bonus + dwell_bonus
        return max(0.0, min(1.0, raw))

    def reset(self) -> None:
        self.stage = self.IDLE
        self.confidence = 0.0
        self._stage_start = 0.0
        self._direction_history.clear()
        self._lock_dwell_ms = 0.0
        self._prev_mag = 0.0
        self._velocity_coherence = 0.0
        self._directional_stability = 0.0


# ──────────────────────────────────────────────────────────────────────
# Temporal Harmonizer (cross-layer smoothing + overcorrection prevention)
# ──────────────────────────────────────────────────────────────────────

class TemporalHarmonizer:
    """Prevents overcorrection between stacked aim engines.

    When multiple engines (PD, snap, micro-adjust, head-assist, etc.) all
    apply corrections in the same frame, the cumulative effect can overshoot.
    The harmonizer:

    1. Tracks the net correction per frame and detects when corrections
       are fighting each other (opposing signs on the same axis).
    2. Applies temporal smoothing that's faster when corrections are
       consistent and slower when they oscillate.
    3. Prevents the output from reversing direction within a short window
       (overcorrection guard).
    """

    def __init__(self) -> None:
        self._prev_out_rx: float = 0.0
        self._prev_out_ry: float = 0.0
        self._prev_in_rx: float = 0.0
        self._prev_in_ry: float = 0.0
        self._correction_rx: float = 0.0
        self._correction_ry: float = 0.0
        self._direction_changes_x: int = 0
        self._direction_changes_y: int = 0
        self._window_start: float = 0.0
        self._window_ms: float = 100.0
        self._smooth_alpha: float = 0.35
        self._guard_ms: float = 30.0
        self._last_direction_change: float = 0.0

    def apply(self, rx: float, ry: float, input_rx: float, input_ry: float,
              delta_ms: float) -> Tuple[float, float]:
        """Apply temporal harmonization.

        - rx, ry: current output from engines
        - input_rx, input_ry: original raw input
        - delta_ms: frame time
        """
        now = time.monotonic()

        # Track direction changes (overcorrection detection)
        if self._prev_in_rx != 0 and input_rx != 0:
            if (rx - input_rx) * (self._prev_out_rx - self._prev_in_rx) < 0:
                self._direction_changes_x += 1
                self._last_direction_change = now
            if (ry - input_ry) * (self._prev_out_ry - self._prev_in_ry) < 0:
                self._direction_changes_y += 1

        # Reset window periodically
        if now - self._window_start > self._window_ms:
            self._direction_changes_x = 0
            self._direction_changes_y = 0
            self._window_start = now

        # Adaptive alpha: faster when corrections are consistent,
        # slower when oscillating (many direction changes)
        osc_x = min(self._direction_changes_x, 5)
        osc_y = min(self._direction_changes_y, 5)
        alpha_x = self._smooth_alpha * (1.0 + osc_x * 0.15)
        alpha_y = self._smooth_alpha * (1.0 + osc_y * 0.15)

        # Clamp alpha to prevent too-slow response
        alpha_x = min(0.85, max(0.15, alpha_x))
        alpha_y = min(0.85, max(0.15, alpha_y))

        # Apply temporal smoothing
        out_rx = self._prev_out_rx + alpha_x * (rx - self._prev_out_rx)
        out_ry = self._prev_out_ry + alpha_y * (ry - self._prev_out_ry)

        # Overcorrection guard: if direction changed very recently,
        # dampen the output to prevent fighting
        time_since_change = (now - self._last_direction_change) * 1000.0
        if time_since_change < self._guard_ms:
            guard_factor = 0.5 + 0.5 * (time_since_change / self._guard_ms)
            out_rx = out_rx * guard_factor + self._prev_out_rx * (1.0 - guard_factor)
            out_ry = out_ry * guard_factor + self._prev_out_ry * (1.0 - guard_factor)

        self._prev_out_rx = out_rx
        self._prev_out_ry = out_ry
        self._prev_in_rx = input_rx
        self._prev_in_ry = input_ry

        return max(-32767.0, min(32767.0, out_rx)), \
               max(-32767.0, min(32767.0, out_ry))

    def reset(self) -> None:
        self._prev_out_rx = 0.0
        self._prev_out_ry = 0.0
        self._prev_in_rx = 0.0
        self._prev_in_ry = 0.0
        self._direction_changes_x = 0
        self._direction_changes_y = 0
        self._last_direction_change = 0.0


# ──────────────────────────────────────────────────────────────────────
# Aim Error Feedback Loop
# ──────────────────────────────────────────────────────────────────────

class AimErrorTracker:
    """Tracks the cumulative error between intended and actual aim.

    Maintains a rolling error signal that downstream engines can use to
    adapt their behavior. High error → increase assistance; low error →
    back off to avoid overcorrection.
    """

    def __init__(self, window_size: int = 20) -> None:
        self._window_size = window_size
        self._errors: List[float] = []
        self._ema_error: float = 0.0
        self._ema_alpha: float = 0.2
        self._peak_error: float = 0.0
        self._consecutive_low: int = 0

    @property
    def smoothed_error(self) -> float:
        return self._ema_error

    @property
    def error_trend(self) -> float:
        """Positive = error increasing, negative = decreasing."""
        if len(self._errors) < 5:
            return 0.0
        recent = self._errors[-5:]
        older = self._errors[-10:-5] if len(self._errors) >= 10 else self._errors[:5]
        return sum(recent) / len(recent) - sum(older) / max(len(older), 1)

    @property
    def is_converged(self) -> bool:
        return self._consecutive_low > 5

    def update(self, intended_rx: float, intended_ry: float,
               actual_rx: float, actual_ry: float) -> None:
        """Record the error between what was intended and what was output."""
        error = math.hypot(actual_rx - intended_rx, actual_ry - intended_ry)
        self._errors.append(error)
        if len(self._errors) > self._window_size:
            self._errors.pop(0)
        self._ema_error += self._ema_alpha * (error - self._ema_error)
        self._peak_error = max(self._peak_error * 0.99, error)
        if error < 200:
            self._consecutive_low += 1
        else:
            self._consecutive_low = 0

    def reset(self) -> None:
        self._errors.clear()
        self._ema_error = 0.0
        self._peak_error = 0.0
        self._consecutive_low = 0


# ──────────────────────────────────────────────────────────────────────
# NeuralTrackerEngine (main composite engine)
# ──────────────────────────────────────────────────────────────────────

class NeuralTrackerEngine:
    """Third-generation aim assist: Kalman prediction + engagement confidence
    + micro-corrections + temporal harmonization + error feedback.

    Sits on top of all existing engines. The pipeline order is:

      [existing engines] → NeuralTrackerEngine.apply() → output

    All parameters are self-contained and tunable. When disabled, returns
    input unchanged (zero-cost passthrough).
    """

    def __init__(self) -> None:
        self.enabled: bool = False

        # Kalman filter
        self.kalman = _Kalman2D()
        self.kalman_measurement_noise: float = 500.0
        self.kalman_lead_ms: float = 25.0

        # Micro-corrections
        self.micro_engine = _MicroCorrectionEngine()
        self.micro_amplitude: float = 180.0

        # Engagement
        self.engagement = AdaptiveEngagementState()

        # Harmonizer
        self.harmonizer = TemporalHarmonizer()

        # Error tracker
        self.error_tracker = AimErrorTracker()

        # Config
        self.confidence_scale: float = 1.0  # global multiplier
        self.kalman_weight: float = 0.6  # blend of kalman vs raw prediction
        self.micro_enabled: bool = True
        self.harmonizer_enabled: bool = True
        self.error_feedback_enabled: bool = True

        # Internal
        self._prev_rx: float = 0.0
        self._prev_ry: float = 0.0

    def apply(self, rx: float, ry: float, raw_rx: float, raw_ry: float,
              is_shooting: bool, is_aiming: bool,
              delta_ms: float) -> Tuple[float, float]:
        """Apply the full neural tracking pipeline.

        - rx, ry: current output from all previous engines
        - raw_rx, raw_ry: original raw input (before any processing)
        - is_shooting, is_aiming: engagement flags
        - delta_ms: frame time in ms

        Returns corrected (rx, ry).
        """
        if not self.enabled:
            return rx, ry

        dt_s = max(delta_ms / 1000.0, 1e-6)

        # 1. Update engagement confidence
        self.engagement.update(rx, ry, is_shooting, delta_ms)
        confidence = self.engagement.confidence * self.confidence_scale

        # 2. Kalman filter: update with current measurement, predict lead
        self.kalman.predict(dt_s)
        self.kalman.update(rx, ry, self.kalman_measurement_noise)
        lead_x, lead_y = self.kalman.predict_lead(self.kalman_lead_ms)

        # Blend kalman lead with raw prediction
        kalman_component = confidence * self.kalman_weight
        rx += lead_x * kalman_component
        ry += lead_y * kalman_component

        # 3. Micro-corrections (multi-frequency sub-pixel)
        if self.micro_enabled and confidence > 0.15:
            rx, ry = self.micro_engine.apply(
                rx, ry, confidence, self.micro_amplitude,
                delta_ms, humanize=True,
            )

        # 4. Error feedback: if error is high, boost corrections
        if self.error_feedback_enabled:
            self.error_tracker.update(raw_rx, raw_ry, rx, ry)
            error = self.error_tracker.smoothed_error
            if error > 500 and not self.error_tracker.is_converged:
                # Error trending up → apply corrective bias
                trend = self.error_tracker.error_trend
                if abs(trend) > 10:
                    bias = min(0.08, abs(trend) / 5000.0) * math.copysign(1.0, -trend)
                    rx = rx * (1.0 + bias)
                    ry = ry * (1.0 + bias)

        # 5. Temporal harmonization (overcorrection prevention)
        if self.harmonizer_enabled:
            rx, ry = self.harmonizer.apply(rx, ry, raw_rx, raw_ry, delta_ms)

        self._prev_rx = rx
        self._prev_ry = ry

        return max(-32767.0, min(32767.0, rx)), max(-32767.0, min(32767.0, ry))

    def reset(self) -> None:
        self.kalman.reset()
        self.micro_engine.reset()
        self.engagement.reset()
        self.harmonizer.reset()
        self.error_tracker.reset()
        self._prev_rx = 0.0
        self._prev_ry = 0.0
