#!/usr/bin/env python3

import time
import functools
from typing import Any, Callable, Dict, Optional, Tuple
from collections import OrderedDict
import threading

class LRUCache:

    def __init__(self, capacity: int = 128):
        self._capacity = capacity
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._capacity:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        return len(self._cache)

class PhysicsLookupTable:

    def __init__(self, table_size: int = 1024):
        self._table_size = table_size
        self._tables: Dict[str, list] = {}
        self._cache = LRUCache(64)

    def generate_curve_table(self, curve_name: str,
                           curve_func: Callable[[float], float]) -> None:
        table = []
        for i in range(self._table_size):
            x = i / (self._table_size - 1)
            y = curve_func(x)
            table.append((x, y))
        self._tables[curve_name] = table

    def get_curve_value(self, curve_name: str, input_value: float) -> float:
        cache_key = f"{curve_name}:{input_value:.6f}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        table = self._tables.get(curve_name)
        if not table:
            return input_value

        input_value = max(0.0, min(1.0, input_value))
        index = input_value * (self._table_size - 1)
        i = int(index)

        if i >= self._table_size - 1:
            result = table[-1][1]
        else:
            t = index - i
            y0 = table[i][1]
            y1 = table[i + 1][1]
            result = y0 + t * (y1 - y0)

        self._cache.put(cache_key, result)
        return result

    def preload_common_curves(self) -> None:
        import math

        linear = lambda x: x
        ease_in = lambda x: x * x
        ease_out = lambda x: 1 - (1 - x) * (1 - x)
        ease_in_out = lambda x: 2 * x * x if x < 0.5 else 1 - 2 * (1 - x) * (1 - x)

        self.generate_curve_table("linear", linear)
        self.generate_curve_table("ease_in", ease_in)
        self.generate_curve_table("ease_out", ease_out)
        self.generate_curve_table("ease_in_out", ease_in_out)

class PerformanceMonitor:

    def __init__(self):
        self._metrics: Dict[str, list] = {}
        self._counters: Dict[str, int] = {}
        self._timers: Dict[str, float] = {}

    def start_timer(self, name: str) -> None:
        self._timers[name] = time.perf_counter()

    def stop_timer(self, name: str) -> float:
        if name in self._timers:
            elapsed = time.perf_counter() - self._timers[name]
            del self._timers[name]

            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(elapsed)

            if len(self._metrics[name]) > 1000:
                self._metrics[name] = self._metrics[name][-500:]

            return elapsed
        return 0.0

    def increment_counter(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_average(self, name: str) -> float:
        values = self._metrics.get(name, [])
        if not values:
            return 0.0
        return sum(values) / len(values)

    def get_percentile(self, name: str, percentile: float) -> float:
        values = self._metrics.get(name, [])
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_all_metrics(self) -> Dict[str, Any]:
        return {
            "timers": {
                name: {
                    "count": len(values),
                    "avg": self.get_average(name),
                    "p50": self.get_percentile(name, 50),
                    "p95": self.get_percentile(name, 95),
                    "p99": self.get_percentile(name, 99),
                }
                for name, values in self._metrics.items()
            },
            "counters": dict(self._counters),
        }

    def reset(self) -> None:
        self._metrics.clear()
        self._counters.clear()
        self._timers.clear()

def timed(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        monitor = get_performance_monitor()
        monitor.start_timer(func.__name__)
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            monitor.stop_timer(func.__name__)
    return wrapper

def cached(maxsize: int = 128) -> Callable:
    def decorator(func: Callable) -> Callable:
        cache = LRUCache(maxsize)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(sorted(kwargs.items()))
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
        return wrapper
    return decorator

_performance_monitor: Optional[PerformanceMonitor] = None
_lookup_table: Optional[PhysicsLookupTable] = None

def get_performance_monitor() -> PerformanceMonitor:
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

def get_lookup_table() -> PhysicsLookupTable:
    global _lookup_table
    if _lookup_table is None:
        _lookup_table = PhysicsLookupTable()
        _lookup_table.preload_common_curves()
    return _lookup_table
