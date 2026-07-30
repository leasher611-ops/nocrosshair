#!/usr/bin/env python3

import time
import sys
sys.path.insert(0, '.')

from nocrosshair.core.performance import (
    LRUCache, PhysicsLookupTable, PerformanceMonitor,
    timed, cached, get_performance_monitor, get_lookup_table
)

def test_lru_cache():
    cache = LRUCache(capacity=3)

    cache.put('key1', 'value1')
    cache.put('key2', 'value2')
    cache.put('key3', 'value3')
    assert cache.size() == 3

    cache.put('key4', 'value4')
    assert cache.size() == 3
    assert cache.get('key1') is None
    assert cache.get('key4') == 'value4'

    cache.get('key2')
    cache.put('key5', 'value5')
    assert cache.get('key3') is None

    print('✓ test_lru_cache passed')

def test_physics_lookup_table():
    lookup = PhysicsLookupTable()

    lookup.generate_curve_table('linear', lambda x: x)
    value = lookup.get_curve_value('linear', 0.5)
    assert abs(value - 0.5) < 0.001

    lookup.generate_curve_table('quadratic', lambda x: x ** 2)
    value = lookup.get_curve_value('quadratic', 0.5)
    assert abs(value - 0.25) < 0.001

    lookup.preload_common_curves()
    linear_val = lookup.get_curve_value('linear', 0.5)
    ease_out_val = lookup.get_curve_value('ease_out', 0.5)
    assert abs(linear_val - 0.5) < 0.001
    assert abs(ease_out_val - 0.75) < 0.001

    print('✓ test_physics_lookup_table passed')

def test_performance_monitor():
    monitor = PerformanceMonitor()

    monitor.start_timer('test')
    time.sleep(0.001)
    elapsed = monitor.stop_timer('test')
    assert elapsed > 0

    monitor.increment_counter('counter', 5)
    assert monitor.get_counter('counter') == 5

    avg = monitor.get_average('test')
    assert avg > 0

    metrics = monitor.get_all_metrics()
    assert 'timers' in metrics
    assert 'counters' in metrics

    print('✓ test_performance_monitor passed')

def test_timed_decorator():
    @timed
    def test_func():
        return 42

    result = test_func()
    assert result == 42

    monitor = get_performance_monitor()
    assert 'test_func' in monitor.get_all_metrics()['timers']

    print('✓ test_timed_decorator passed')

def test_cached_decorator():
    call_count = 0

    @cached()
    def expensive_func(n):
        nonlocal call_count
        call_count += 1
        return n ** 2

    result1 = expensive_func(10)
    assert result1 == 100

    result2 = expensive_func(10)
    assert result2 == 100

    result3 = expensive_func(20)
    assert result3 == 400

    print('✓ test_cached_decorator passed')

def test_global_instances():
    monitor = get_performance_monitor()
    assert isinstance(monitor, PerformanceMonitor)

    lookup = get_lookup_table()
    assert isinstance(lookup, PhysicsLookupTable)

    print('✓ test_global_instances passed')

def run_all_tests():
    print('Running performance tests...')

    test_lru_cache()
    test_physics_lookup_table()
    test_performance_monitor()
    test_timed_decorator()
    test_cached_decorator()
    test_global_instances()

    print('\\n✅ All performance tests passed')

if __name__ == '__main__':
    run_all_tests()
