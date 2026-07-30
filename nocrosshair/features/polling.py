from __future__ import annotations

import math
import time
from enum import Enum
from collections import deque


class PollingPrecision(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class PollingEngine:
    def __init__(self, rate_hz: int) -> None:
        if rate_hz <= 0:
            raise ValueError(f"Polling rate must be positive: {rate_hz}")
        self._rate_hz = rate_hz
        self._interval_ns = int(1_000_000_000 / rate_hz)

        if rate_hz >= 8000:
            self._precision = PollingPrecision.ULTRA
        elif rate_hz >= 1000:
            self._precision = PollingPrecision.HIGH
        elif rate_hz >= 250:
            self._precision = PollingPrecision.MEDIUM
        else:
            self._precision = PollingPrecision.LOW

    @property
    def rate_hz(self) -> int:
        return self._rate_hz

    @property
    def interval_ns(self) -> int:
        return self._interval_ns

    @property
    def precision(self) -> PollingPrecision:
        return self._precision

    def sleep_until(self, next_time_ns: int) -> None:
        now = self.now_ns()
        delta = next_time_ns - now
        if delta <= 0:
            return

        prec = self._precision
        if prec == PollingPrecision.ULTRA:
            while self.now_ns() < next_time_ns:
                pass
        elif prec == PollingPrecision.HIGH:
            if delta > 500_000:
                time.sleep((delta - 200_000) / 1_000_000_000.0)
            while self.now_ns() < next_time_ns:
                pass
        elif prec == PollingPrecision.MEDIUM:
            if delta > 1_000_000:
                time.sleep((delta - 500_000) / 1_000_000_000.0)
            while self.now_ns() < next_time_ns:
                pass
        else:
            time.sleep(delta / 1_000_000_000.0)

    def now_ns(self) -> int:
        return time.monotonic_ns()

    def compute_next(self, now_ns: int) -> int:
        return now_ns + self._interval_ns


class PollingStats:
    def __init__(self, window_size: int = 100) -> None:
        self._window_size = window_size
        self._intervals: deque[int] = deque(maxlen=window_size)
        self._missed: int = 0
        self._total_cycles: int = 0

    def record_cycle(self, actual_interval_ns: int) -> None:
        self._intervals.append(actual_interval_ns)
        self._total_cycles += 1
        if actual_interval_ns <= 0:
            self._missed += 1

    @property
    def actual_rate_hz(self) -> float:
        if len(self._intervals) == 0:
            return 0.0
        avg_ns = sum(self._intervals) / len(self._intervals)
        if avg_ns <= 0:
            return 0.0
        return 1_000_000_000.0 / avg_ns

    @property
    def jitter_ns(self) -> float:
        if len(self._intervals) < 2:
            return 0.0
        mean = sum(self._intervals) / len(self._intervals)
        variance = sum((x - mean) ** 2 for x in self._intervals) / len(self._intervals)
        return math.sqrt(variance)

    @property
    def missed_cycles(self) -> int:
        return self._missed

    @property
    def total_cycles(self) -> int:
        return self._total_cycles

    def reset(self) -> None:
        self._intervals.clear()
        self._missed = 0
        self._total_cycles = 0
