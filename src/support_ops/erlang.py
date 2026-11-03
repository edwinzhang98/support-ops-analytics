"""Erlang C staffing formulas.

Erlang C answers: "if tickets arrive at random (Poisson) at rate lam per hour,
each takes on average `aht_min` minutes of agent time, and N agents work the
queue first-come-first-served, what share of tickets wait no longer than
`t_min` minutes?"  Turned around, it gives the smallest N that reaches a
service-level goal.

Notation (per interval)
    lam       arrivals per hour
    aht_min   average handle time, minutes
    A         traffic intensity in Erlangs = lam * aht_min / 60
              (= agents' worth of work arriving, e.g. A = 3.2 -> 3.2 agents busy on average)
    N         productive agents on the floor
    t_min     target answer time, minutes

Conventions follow pyworkforce.ErlangC: add agents from the traffic intensity
until the SLA goal is met; if occupancy A/N then exceeds the cap, raise N to
ceil(A / max_occupancy); apply shrinkage last: scheduled = ceil(N / (1 - s)).

Key assumptions (see docs/assumptions.md): Poisson arrivals, exponential
handle times, no abandonment, steady state within each interval, FCFS.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def traffic_intensity(lam_per_hour: float, aht_min: float) -> float:
    return lam_per_hour * aht_min / 60.0


def erlang_b(n: int, a: float) -> float:
    """Blocking probability, by the numerically stable recursion B(k) = aB(k-1) / (k + aB(k-1))."""
    b = 1.0
    for k in range(1, n + 1):
        b = a * b / (k + a * b)
    return b


def erlang_c(n: int, a: float) -> float:
    """Probability that an arriving ticket has to wait (all N agents busy)."""
    if a <= 0:
        return 0.0
    if n <= a:
        return 1.0
    b = erlang_b(n, a)
    return n * b / (n - a * (1.0 - b))


def service_level(n: int, a: float, aht_min: float, t_min: float) -> float:
    """Share of tickets answered within t_min: 1 - C(N, A) * exp(-(N - A) * t / AHT)."""
    if a <= 0:
        return 1.0
    if n <= a:
        return 0.0
    return 1.0 - erlang_c(n, a) * math.exp(-(n - a) * t_min / aht_min)


def asa_min(n: int, a: float, aht_min: float) -> float:
    """Average speed of answer (mean wait), minutes."""
    if a <= 0:
        return 0.0
    if n <= a:
        return math.inf
    return erlang_c(n, a) * aht_min / (n - a)


def service_level_fractional(p: float, a: float, aht_min: float, t_min: float) -> float:
    """Service level for a fractional number of agents p (e.g. 6.3 productive after shrinkage).

    Interpreted as floor(p) agents for (1 - frac) of the time and floor(p) + 1 for frac of
    the time, which is how the simulation samples staffing (support_ops.simulation).
    """
    lo = math.floor(p)
    frac = p - lo
    sl_lo = service_level(lo, a, aht_min, t_min)
    if frac == 0:
        return sl_lo
    return (1 - frac) * sl_lo + frac * service_level(lo + 1, a, aht_min, t_min)


def required_agents(lam_per_hour: float, aht_min: float, t_min: float, sl_goal: float,
                    max_occupancy: float = 1.0, min_agents: int = 0) -> int:
    """Smallest number of productive agents meeting the SLA goal and the occupancy cap."""
    if lam_per_hour <= 0:
        return min_agents
    a = traffic_intensity(lam_per_hour, aht_min)
    n = max(math.floor(a) + 1, 1)          # need N > A for a stable queue
    while service_level(n, a, aht_min, t_min) < sl_goal:
        n += 1
    n = max(n, math.ceil(a / max_occupancy - 1e-9))
    return max(n, min_agents)


def scheduled_agents(productive: float, shrinkage: float) -> int:
    """People to schedule so that `productive` are available after shrinkage."""
    return math.ceil(productive / (1.0 - shrinkage) - 1e-9)


def requirement_table(lam: pd.Series | np.ndarray, aht_min: float, t_min: float, sl_goal: float,
                      max_occupancy: float = 1.0, min_agents: int = 0) -> pd.DataFrame:
    """Vectorised over intervals: traffic, required agents, achieved SL, occupancy, ASA."""
    lam = np.asarray(lam, dtype=float)
    rows = []
    for x in lam:
        a = traffic_intensity(x, aht_min)
        n = required_agents(x, aht_min, t_min, sl_goal, max_occupancy, min_agents)
        rows.append({
            "arrivals_per_hour": x,
            "erlangs": a,
            "agents_required": n,
            "service_level": service_level(n, a, aht_min, t_min) if n > 0 else (1.0 if a == 0 else 0.0),
            "occupancy": a / n if n > 0 else 0.0,
            "asa_min": asa_min(n, a, aht_min) if n > 0 else 0.0,
        })
    return pd.DataFrame(rows)
