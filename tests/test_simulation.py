import numpy as np
import pytest

from support_ops.erlang import asa_min, service_level, traffic_intensity
from support_ops.simulation import productive_servers, simulate_blended, simulate_fcfs


def poisson_stream(rng, lam_per_hour, hours, aht_min):
    n = rng.poisson(lam_per_hour * hours)
    arr = np.sort(rng.uniform(0, hours * 3600, n))
    svc = rng.exponential(aht_min * 60, n)
    return arr, svc


@pytest.mark.parametrize("lam,aht,c,t", [(24, 10, 6, 2), (60, 6, 8, 1), (5, 12, 2, 2)])
def test_fcfs_matches_erlang_c(lam, aht, c, t):
    """Constant staffing + Poisson arrivals + exponential handle times = Erlang C's world."""
    rng = np.random.default_rng(7)
    hours = 20000
    arr, svc = poisson_stream(rng, lam, hours, aht)
    start = simulate_fcfs(arr, svc, np.full(hours + 50, c))
    wait_min = (start - arr) / 60
    a = traffic_intensity(lam, aht)
    assert np.mean(wait_min <= t) == pytest.approx(service_level(c, a, aht, t), abs=0.01)
    assert np.mean(wait_min) == pytest.approx(asa_min(c, a, aht), rel=0.06, abs=0.05)


def test_blended_without_live_equals_fcfs():
    rng = np.random.default_rng(3)
    arr, svc = poisson_stream(rng, 30, 2000, 6)
    servers = np.full(2100, 4)
    s1 = simulate_fcfs(arr, svc, servers)
    s2 = simulate_blended(arr, svc, np.zeros(len(arr), bool), servers)["start"]
    assert np.allclose(s1, s2)


def test_live_work_sees_whole_pool_under_preemption():
    """With preemption, live contacts behave like an Erlang C queue over ALL agents,
    no matter how much async work is waiting."""
    rng = np.random.default_rng(11)
    hours = 20000
    la, sa = poisson_stream(rng, 6, hours, 10)       # live: 1.0 Erlang
    aa, asv = poisson_stream(rng, 20, hours, 6)      # async: 2.0 Erlangs
    arr = np.concatenate([la, aa])
    svc = np.concatenate([sa, asv])
    live = np.concatenate([np.ones(len(la), bool), np.zeros(len(aa), bool)])
    res = simulate_blended(arr, svc, live, np.full(hours + 50, 4))
    wait = (res["start"] - arr) / 60
    sl_live = np.mean(wait[live] <= 2)
    assert sl_live == pytest.approx(service_level(4, 1.0, 10, 2), abs=0.01)
    # async work still gets done (queue is stable at 75% total occupancy)
    assert np.isfinite(res["finish"]).all()


def test_no_agents_means_waiting_for_next_shift():
    arr = np.array([100.0, 200.0])
    svc = np.array([60.0, 60.0])
    servers = np.array([0, 1, 1])
    start = simulate_fcfs(arr, svc, servers)
    assert start[0] == 3600.0 and start[1] == 3660.0


def test_productive_servers_average():
    rng = np.random.default_rng(0)
    out = productive_servers(np.full(100000, 9), 0.3, rng)
    assert out.mean() == pytest.approx(6.3, abs=0.02)
    assert set(np.unique(out)) == {6, 7}
