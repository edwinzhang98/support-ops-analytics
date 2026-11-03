import json

import numpy as np
import pandas as pd
import pytest

from support_ops import interactive
from support_ops.config import load_config, processed_path

pytestmark = pytest.mark.skipif(not processed_path("staff_demand.parquet").exists(),
                                reason="run `python run.py` first")


def test_staffing_whatif_reproduces_base_case():
    cfg = load_config()
    st = cfg["staffing"]
    demand = pd.read_parquet(processed_path("staff_demand.parquet"))
    cov = pd.read_parquet(processed_path("staff_coverage.parquet"))
    kn = json.load(open(processed_path("x").parents[2] / "reports" / "key_numbers.json"))
    out = interactive.staffing_whatif(demand, st, cov["scheduled_by_day"].to_numpy(), sl_goal=st["sl_goal"],
                                      max_occupancy=st["max_occupancy"], shrinkage=st["shrinkage"])
    assert out["fte_needed"] == kn["staff_fte_current"]
    assert out["hours_today_short"] == kn["staff_hours_under_today_by_day"]


def test_more_shrinkage_needs_more_people():
    cfg = load_config()
    st = cfg["staffing"]
    demand = pd.read_parquet(processed_path("staff_demand.parquet"))
    today = np.full(168, 6.0)
    lo = interactive.staffing_whatif(demand, st, today, sl_goal=0.9, max_occupancy=0.85, shrinkage=0.2)
    hi = interactive.staffing_whatif(demand, st, today, sl_goal=0.9, max_occupancy=0.85, shrinkage=0.4)
    assert hi["fte_needed"] > lo["fte_needed"]


def test_costed_options_hire_cost_scales_with_fte_cost():
    opts = pd.read_parquet(processed_path("business_options.parquet"))
    a = interactive.costed_options(opts, 60000, 5000, 40000, 25000, 2.2)
    b = interactive.costed_options(opts, 70000, 5000, 40000, 25000, 2.2)
    hire_a = a.loc[a.option == "A. Hire", "annual_cost_change_eur"].iloc[0]
    hire_b = b.loc[b.option == "A. Hire", "annual_cost_change_eur"].iloc[0]
    assert hire_b - hire_a == pytest.approx(10000 * (a.loc[a.option == "A. Hire", "fte"].iloc[0] - 24))
    assert a.loc[a.option == "B. Re-roster", "first_year_cost_eur"].iloc[0] == 0


def test_heatmap_filtered_totals():
    fct = pd.read_parquet(processed_path("fct_tickets.parquet"))
    h = interactive.heatmap_filtered(fct, channels=["Email"])
    assert h["tickets"].sum() == (fct["channel"] == "Email").sum()
    assert len(h) == 168
