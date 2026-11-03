"""Rosters: turn an hourly requirement into 8-hour shifts.

A roster here is the number of agents starting an 8-hour shift at each allowed
start time on each day of the week. Coverage of hour h = agents whose shift spans h.

* optimize_min_shifts   : fewest weekly shifts that cover the requirement in every hour
                          (integer program, scipy.optimize.milp / HiGHS)
* optimize_fixed_budget : with a fixed number of weekly shifts (same headcount), cover
                          the requirement as evenly as possible (maximise the worst
                          hour's coverage ratio)
* hypothesis rosters    : what today's roster might look like (no roster data exists):
                          flat, proportional-by-day, business-hours-weighted
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def shift_catalogue(starts: list[int], shift_len: int = 8) -> pd.DataFrame:
    rows = [{"day": d, "day_name": DAYS[d], "start": s,
             "label": f"{s:02d}:00-{(s + shift_len) % 24:02d}:00"}
            for d in range(7) for s in starts]
    return pd.DataFrame(rows)


def coverage_matrix(shifts: pd.DataFrame, shift_len: int = 8) -> np.ndarray:
    """168 x n_shifts matrix: 1 if the shift covers that hour of the week (wraps Sun -> Mon)."""
    a = np.zeros((168, len(shifts)))
    for j, (d, s) in enumerate(zip(shifts["day"], shifts["start"])):
        for k in range(shift_len):
            a[(d * 24 + s + k) % 168, j] = 1
    return a


def _day_rows(shifts: pd.DataFrame) -> np.ndarray:
    return np.vstack([(shifts["day"] == d).to_numpy(float) for d in range(7)])


def optimize_min_shifts(required: np.ndarray, starts: list[int], shift_len: int = 8) -> pd.DataFrame:
    """Fewest weekly shifts such that scheduled agents >= required in all 168 hours."""
    shifts = shift_catalogue(starts, shift_len)
    a = coverage_matrix(shifts, shift_len)
    res = milp(c=np.ones(len(shifts)),
               constraints=[LinearConstraint(a, lb=np.asarray(required, float), ub=np.inf)],
               integrality=np.ones(len(shifts)), bounds=Bounds(0, np.inf),
               options={"time_limit": 60})
    if not res.success:
        raise RuntimeError(f"roster optimisation failed: {res.message}")
    shifts["agents"] = np.round(res.x).astype(int)
    return shifts


def optimize_fixed_budget(required: np.ndarray, budget_shifts: int, starts: list[int],
                          fte: int, weights: np.ndarray | None = None,
                          shift_len: int = 8) -> pd.DataFrame:
    """Same headcount, best spread: maximise min_h coverage(h) / required(h).

    Constraints: exactly `budget_shifts` shifts per week; at most `fte` shifts on a day
    (one shift per person per day). Tie-break: put spare capacity where volume is
    (tiny secondary weight on volume-weighted coverage).
    """
    shifts = shift_catalogue(starts, shift_len)
    a = coverage_matrix(shifts, shift_len)
    req = np.asarray(required, float)
    n = len(shifts)
    w = np.ones(168) if weights is None else np.asarray(weights, float) / np.mean(weights)
    # variables: x_1..x_n (integer), t (continuous)
    c = np.concatenate([-1e-4 * (w @ a) / 168, [-1.0]])
    cons = [
        LinearConstraint(np.hstack([a, -req[:, None]]), lb=0, ub=np.inf),          # cover >= t * req
        LinearConstraint(np.concatenate([np.ones(n), [0]])[None, :], lb=budget_shifts, ub=budget_shifts),
        LinearConstraint(np.hstack([_day_rows(shifts), np.zeros((7, 1))]), lb=0, ub=fte),
    ]
    res = milp(c=c, constraints=cons, integrality=np.concatenate([np.ones(n), [0]]),
               bounds=Bounds(0, np.inf), options={"time_limit": 60})
    if not res.success:
        raise RuntimeError(f"roster optimisation failed: {res.message}")
    shifts["agents"] = np.round(res.x[:n]).astype(int)
    shifts.attrs["min_coverage_ratio"] = float(res.x[-1])
    return shifts


def coverage_from_shifts(shifts: pd.DataFrame, shift_len: int = 8) -> np.ndarray:
    return coverage_matrix(shifts, shift_len) @ shifts["agents"].to_numpy(float)


def roster_table(shifts: pd.DataFrame) -> pd.DataFrame:
    """Shift x day table of agents starting each shift (the format WFM uses)."""
    shifts = shifts.copy()
    shifts.attrs = {}
    t = shifts.pivot_table(index="label", columns="day_name", values="agents", aggfunc="sum")
    t = t.reindex(columns=DAYS).fillna(0).astype(int)
    order = sorted(t.index, key=lambda s: int(s[:2]))
    t = t.loc[order]
    t.loc["Total shifts"] = t.sum()
    return t


# ---------------------------------------------------------------------------
# Hypotheses for today's roster (no roster data in the export)
# ---------------------------------------------------------------------------
def _largest_remainder(values: np.ndarray, total: int) -> np.ndarray:
    base = np.floor(values).astype(int)
    short = total - base.sum()
    if short > 0:
        order = np.argsort(-(values - base), kind="stable")
        base[order[:short]] += 1
    return base


HYPOTHESES = {
    "flat": "Flat 24/7: same headcount on every shift, every day (3 x 8h shifts)",
    "by_day": "Weekday-weighted: daily headcount proportional to daily NEW-ticket volume, 3 equal shifts",
    "business_hours": "Day-weighted: daily headcount proportional to volume; 47% of each day's "
                      "shifts on 08-16, 27% on 00-08 and 27% on 16-24 (60% of hours in 08-20)",
}


def hypothesis_roster(kind: str, budget_shifts: int, daily_share: np.ndarray) -> pd.DataFrame:
    """Today's-roster hypothesis with `budget_shifts` weekly 8h shifts (starts 00/08/16)."""
    shifts = shift_catalogue([0, 8, 16])
    daily_share = np.asarray(daily_share, float) / np.sum(daily_share)
    if kind == "flat":
        slot_w = np.full(21, 1 / 21)
    elif kind == "by_day":
        slot_w = np.repeat(daily_share, 3) / 3
    elif kind == "business_hours":
        within = np.array([1.0, 1.75, 1.0]) / 3.75          # night, day, evening
        slot_w = np.repeat(daily_share, 3) * np.tile(within, 7)
    else:
        raise ValueError(kind)
    shifts["agents"] = _largest_remainder(slot_w * budget_shifts, budget_shifts)
    return shifts


def extra_shifts_to_cover(today: pd.DataFrame, required: np.ndarray, starts: list[int],
                          shift_len: int = 8) -> pd.DataFrame:
    """'Hire' option: keep everyone where they are today and add the fewest new shifts
    (on any allowed start time) so that every hour meets the requirement."""
    gap = np.asarray(required, float) - coverage_from_shifts(today, shift_len)
    if np.all(gap <= 0):
        extra = shift_catalogue(starts, shift_len)
        extra["agents"] = 0
        return extra
    extra = optimize_min_shifts(np.maximum(gap, 0), starts, shift_len)
    return extra


def combine_shifts(*rosters: pd.DataFrame) -> pd.DataFrame:
    allr = pd.concat(rosters, ignore_index=True)
    return allr.groupby(["day", "day_name", "start", "label"], as_index=False)["agents"].sum()


def fte_from_shifts(n_shifts: int, shifts_per_fte: int = 5) -> int:
    return math.ceil(n_shifts / shifts_per_fte)
