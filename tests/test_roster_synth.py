import numpy as np
import pandas as pd
import pytest

from support_ops import roster, synth
from support_ops.config import load_config, processed_path


def test_min_shifts_covers_requirement_and_is_tight():
    rng = np.random.default_rng(5)
    req = rng.integers(1, 7, 168).astype(float)
    sh = roster.optimize_min_shifts(req, [0, 8, 12, 16])
    cov = roster.coverage_from_shifts(sh)
    assert np.all(cov >= req)
    assert sh["agents"].sum() >= np.ceil(req.sum() / 8)          # lower bound: hours / shift length


def test_fixed_budget_uses_exact_budget_and_daily_cap():
    req = np.full(168, 4.0)
    sh = roster.optimize_fixed_budget(req, budget_shifts=100, starts=[0, 8, 16], fte=20)
    assert sh["agents"].sum() == 100
    assert sh.groupby("day")["agents"].sum().max() <= 20


@pytest.mark.parametrize("kind", ["flat", "by_day", "business_hours"])
def test_hypothesis_roster_keeps_budget(kind):
    share = np.array([8, 7, 8, 7, 7, 3, 4], float)
    sh = roster.hypothesis_roster(kind, 120, share)
    assert sh["agents"].sum() == 120


def test_extra_shifts_close_every_gap():
    share = np.array([8, 7, 8, 7, 7, 3, 4], float)
    today = roster.hypothesis_roster("by_day", 120, share)
    req = np.full(168, 5.0)
    extra = roster.extra_shifts_to_cover(today, req, [0, 8, 12, 16])
    cov = roster.coverage_from_shifts(roster.combine_shifts(today, extra))
    assert np.all(cov >= req)


def test_follow_up_semantics():
    inter = np.array([1, 2, 6, 6])
    ch = np.array(["Email", "Chat", "Chat", "Phone"])
    assert synth.follow_up_touches(inter, ch, "touches").tolist() == [0, 1, 5, 5]
    assert synth.follow_up_touches(inter, ch, "half_agent").tolist() == [0, 0, 2, 2]
    assert synth.follow_up_touches(inter, ch, "chat_in_session").tolist() == [0, 0, 0, 5]


@pytest.mark.skipif(not processed_path("fct_tickets.parquet").exists(), reason="run `python run.py` first")
def test_synthetic_mix_matches_real():
    cfg = load_config()
    fct = pd.read_parquet(processed_path("fct_tickets.parquet"))
    t = synth.generate_tickets(fct, cfg, np.random.default_rng(1))
    assert abs(len(t) / len(fct) - cfg["scenario"]["scale_factor"]) < 0.5
    for col in ["channel", "topic", "priority"]:
        gap = (fct[col].value_counts(normalize=True) - t[col].value_counts(normalize=True)).abs().max()
        assert gap < 0.02, (col, gap)
    assert t["created_at"].dt.normalize().isin(pd.to_datetime(synth.HOLIDAYS_2023)).sum() == 0
    assert t["agent_interactions"].between(0, 10).all()
