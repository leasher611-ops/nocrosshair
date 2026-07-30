from __future__ import annotations

import math
import time
import json
import os
from enum import Enum
from typing import Optional


class GyroAimMode(Enum):
    DISABLED = "disabled"
    MOUSE = "mouse"
    STICK = "stick"
    HYBRID = "hybrid"


class GyroConfig:
    def __init__(
        self,
        enabled: bool = False,
        aim_mode: GyroAimMode = GyroAimMode.STICK,
        sensitivity: float = 1.0,
        smoothing: float = 0.5,
        deadzone: float = 0.02,
        space: str = "local",
        invert_y: bool = False,
        invert_x: bool = False,
        rotation_compensation: bool = True,
    ) -> None:
        self.enabled = enabled
        self.aim_mode = aim_mode
        self.sensitivity = sensitivity
        self.smoothing = smoothing
        self.deadzone = deadzone
        self.space = space
        self.invert_y = invert_y
        self.invert_x = invert_x
        self.rotation_compensation = rotation_compensation

    @staticmethod
    def from_dict(d: dict, prefix: str = "gyro_") -> GyroConfig:
        mode_str = d.get(f"{prefix}mode", "stick")
        try:
            mode = GyroAimMode(mode_str)
        except ValueError:
            mode = GyroAimMode.STICK
        return GyroConfig(
            enabled=bool(d.get(f"{prefix}enabled", False)),
            aim_mode=mode,
            sensitivity=float(d.get(f"{prefix}sensitivity", 1.0)),
            smoothing=float(d.get(f"{prefix}smoothing", 0.5)),
            deadzone=float(d.get(f"{prefix}deadzone", 0.02)),
            space=str(d.get(f"{prefix}space", "local")),
            invert_y=bool(d.get(f"{prefix}invert_y", False)),
            invert_x=bool(d.get(f"{prefix}invert_x", False)),
            rotation_compensation=bool(d.get(f"{prefix}rotation_comp", True)),
        )

    def to_dict(self) -> dict:
        return {
            "gyro_enabled": self.enabled,
            "gyro_mode": self.aim_mode.value,
            "gyro_sensitivity": self.sensitivity,
            "gyro_smoothing": self.smoothing,
            "gyro_deadzone": self.deadzone,
            "gyro_space": self.space,
            "gyro_invert_y": self.invert_y,
            "gyro_invert_x": self.invert_x,
            "gyro_rotation_comp": self.rotation_compensation,
        }


class GyroEngine:
    STICK_RANGE = 32767

    def __init__(self, config: GyroConfig) -> None:
        self.config = config
        self._gyro_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._filtered_pitch: float = 0.0
        self._filtered_yaw: float = 0.0
        self._prev_time_ns: int = 0
        self._initialized: bool = False
        self._alpha: float = 0.98

    def process(
        self,
        gyro_data: tuple[float, float, float],
        accel_data: tuple[float, float, float],
    ) -> tuple[int, int]:
        if not self.config.enabled or self.config.aim_mode == GyroAimMode.DISABLED:
            return 0, 0

        now_ns = time.monotonic_ns()
        if not self._initialized:
            self._prev_time_ns = now_ns
            self._initialized = True
            return 0, 0

        dt_s = (now_ns - self._prev_time_ns) / 1_000_000_000.0
        dt_s = max(dt_s, 0.0001)
        self._prev_time_ns = now_ns

        gx, gy, gz = (
            gyro_data[0] - self._gyro_offset[0],
            gyro_data[1] - self._gyro_offset[1],
            gyro_data[2] - self._gyro_offset[2],
        )

        if self.config.space == "local":
            yaw_rate = -gx
            pitch_rate = -gy
        else:
            yaw_rate = -gx
            pitch_rate = -gy

        if self.config.rotation_compensation:
            ax, ay, az = accel_data
            norm_a = math.sqrt(ax * ax + ay * ay + az * az)
            if norm_a > 0.001:
                ax_n, ay_n, az_n = ax / norm_a, ay / norm_a, az / norm_a
                roll = math.atan2(-ax_n, -az_n) if abs(-az_n) > 0.001 else 0.0
                cos_r = math.cos(roll)
                sin_r = math.sin(roll)
                comp_yaw = yaw_rate * cos_r + pitch_rate * sin_r
                comp_pitch = -yaw_rate * sin_r + pitch_rate * cos_r
                yaw_rate, pitch_rate = comp_yaw, comp_pitch

        raw_yaw = yaw_rate * dt_s * self.config.sensitivity * 2000.0
        raw_pitch = pitch_rate * dt_s * self.config.sensitivity * 2000.0

        smooth = self.config.smoothing
        if smooth > 0.0:
            blend = 1.0 - smooth
            self._filtered_yaw = self._filtered_yaw * smooth + raw_yaw * blend
            self._filtered_pitch = self._filtered_pitch * smooth + raw_pitch * blend
        else:
            self._filtered_yaw = raw_yaw
            self._filtered_pitch = raw_pitch

        rx = self._apply_deadzone(int(self._filtered_yaw))
        ry = self._apply_deadzone(int(self._filtered_pitch))

        if self.config.invert_x:
            rx = -rx
        if self.config.invert_y:
            ry = -ry

        rx = max(-self.STICK_RANGE, min(self.STICK_RANGE, rx))
        ry = max(-self.STICK_RANGE, min(self.STICK_RANGE, ry))

        return rx, ry

    def calibrate(self, samples: int = 100) -> tuple[float, float, float]:
        collected: list[tuple[float, float, float]] = []
        for _ in range(samples):
            gx, gy, gz = 0.0, 0.0, 0.0
            collected.append((gx, gy, gz))
            time.sleep(0.001)
        ox = sum(s[0] for s in collected) / samples
        oy = sum(s[1] for s in collected) / samples
        oz = sum(s[2] for s in collected) / samples
        self._gyro_offset = (ox, oy, oz)
        return self._gyro_offset

    def reset_orientation(self) -> None:
        self._filtered_pitch = 0.0
        self._filtered_yaw = 0.0
        self._initialized = False

    def set_offsets(self, offsets: tuple[float, float, float]) -> None:
        self._gyro_offset = offsets

    def _apply_deadzone(self, value: int) -> int:
        if abs(value) < int(self.config.deadzone * self.STICK_RANGE):
            return 0
        return value


class GyroCalibrator:
    @staticmethod
    def collect_samples(duration_s: float = 2.0) -> list:
        samples: list[tuple[float, float, float]] = []
        end = time.monotonic() + duration_s
        while time.monotonic() < end:
            gx, gy, gz = 0.0, 0.0, 0.0
            samples.append((gx, gy, gz))
            time.sleep(0.001)
        return samples

    @staticmethod
    def compute_offsets(samples: list) -> tuple[float, float, float]:
        n = len(samples)
        if n == 0:
            return (0.0, 0.0, 0.0)
        ox = sum(s[0] for s in samples) / n
        oy = sum(s[1] for s in samples) / n
        oz = sum(s[2] for s in samples) / n
        return (ox, oy, oz)

    @staticmethod
    def save_calibration(offsets: tuple[float, float, float], path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump({"gyro_offset_x": offsets[0], "gyro_offset_y": offsets[1], "gyro_offset_z": offsets[2]}, f)
            return True
        except (OSError, PermissionError, TypeError):
            return False

    @staticmethod
    def load_calibration(path: str) -> Optional[tuple[float, float, float]]:
        try:
            if not os.path.isfile(path):
                return None
            with open(path, "r") as f:
                data = json.load(f)
            return (float(data["gyro_offset_x"]), float(data["gyro_offset_y"]), float(data["gyro_offset_z"]))
        except (OSError, PermissionError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            return None
