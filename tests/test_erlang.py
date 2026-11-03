import math

import pytest

from support_ops.erlang import (
    asa_min, erlang_c, required_agents, scheduled_agents, service_level, traffic_intensity,
)


def erlang_c_direct(n: int, a: float) -> float:
    """Textbook factorial form, used only to check the recursive implementation."""
    top = a ** n / math.factorial(n) * n / (n - a)
    bottom = sum(a ** k / math.factorial(k) for k in range(n)) + top
    return top / bottom


@pytest.mark.parametrize("n,a", [(2, 0.5), (5, 3.2), (14, 10.0), (20, 17.5), (40, 35.0)])
def test_erlang_c_matches_factorial_formula(n, a):
    assert erlang_c(n, a) == pytest.approx(erlang_c_direct(n, a), rel=1e-10)


def test_pyworkforce_tutorial_example():
    """pyworkforce docs: 100 transactions / 30 min, AHT 3 min, ASA target 20 s,
    80% service level, max occupancy 85%, shrinkage 30% -> 14 raw positions,
    20 after shrinkage, service level ~0.888, occupancy ~0.714."""
    lam_per_hour = 100 * 2
    aht, t = 3.0, 20 / 60
    n = required_agents(lam_per_hour, aht, t, sl_goal=0.80, max_occupancy=0.85)
    a = traffic_intensity(lam_per_hour, aht)
    assert a == pytest.approx(10.0)
    assert n == 14
    assert scheduled_agents(n, 0.30) == 20
    assert service_level(n, a, aht, t) == pytest.approx(0.888, abs=0.001)
    assert a / n == pytest.approx(0.714, abs=0.001)


def test_service_level_increases_with_agents():
    a, aht, t = 4.0, 10.0, 2.0
    sls = [service_level(n, a, aht, t) for n in range(5, 15)]
    assert all(x < y for x, y in zip(sls, sls[1:]))
    assert sls[-1] > 0.99


def test_edge_cases():
    assert required_agents(0, 10, 2, 0.9, min_agents=1) == 1
    assert service_level(3, 3.0, 10, 2) == 0.0          # unstable queue
    assert asa_min(3, 3.0, 10) == math.inf
    assert required_agents(1.0, 60, 60, 0.9, max_occupancy=0.5) >= 2   # occupancy cap binds
