"""Synthetic scale-up of the real export, for interval-level staffing only.

Why: the export has ~0.3 tickets per hour, so most hour-of-week slots see 0-1
tickets a week and no queue ever forms. Erlang C and the simulation need a stable
arrival rate per hour, so we generate a scaled version of the same year.

What is copied from the real export (calibration):
  * arrival rate by weekday (tickets/day, 7 values) and the hour-of-day profile
    (pooled over days: weekday x hour independence test p = 0.90; 3-hour smoothing)
  * zero volume on the holidays where the export has none (1 Jan, 24-26 Dec, 31 Dec)
  * everything else about a ticket is a bootstrap of a real ticket created in the
    SAME month: channel, priority, topic, product group, tier, country, agent
    interactions, resolution outcome and duration, CSAT, and its first-response
    delay. Month-level resampling keeps the real joint mix and the real
    resolution-time trend (resolution is not modelled by the queue; see RCA).
  * the real first-response delay is used as the ticket's "pickup delay": at the
    export's volume there is no queueing, so the real response times measure how
    quickly agents pick work up, not how long tickets wait for a free agent.

What is NOT in the data and therefore assumed (config.yaml / docs/assumptions.md):
  * the scale factor (20x), handle time per touch, how follow-up touches are
    spread over a ticket's life, what "agent interactions" counts.

Everything is driven by one seeded numpy Generator, so two runs give identical data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HOLIDAYS_2023 = ["2023-01-01", "2023-12-24", "2023-12-25", "2023-12-26", "2023-12-31"]
LIVE_CHANNELS = ("Chat", "Phone")
SECONDS_PER_HOUR = 3600.0

# Interpretations of the `agent_interactions` field (the dataset documents it as
# "total number of agent interactions per ticket"; its distribution differs by channel).
INTERACTION_SEMANTICS = {
    "touches": "Every interaction is a separate agent touch (documented definition)",
    "half_agent": "Interactions count both sides; half of them are agent touches",
    "chat_in_session": "Chat interactions are messages inside one live session; email/phone as touches",
}


# ---------------------------------------------------------------------------
# Calibration from the real export
# ---------------------------------------------------------------------------
def hourly_profile(fct: pd.DataFrame, weights=(0.25, 0.5, 0.25)) -> np.ndarray:
    """Share of daily tickets in each hour (24 values summing to 1), circularly smoothed."""
    counts = fct.groupby("created_hour").size().reindex(range(24), fill_value=0).to_numpy(float)
    w = np.asarray(weights, float)
    k = len(w) // 2
    smoothed = sum(w[i] * np.roll(counts, i - k) for i in range(len(w)))
    return smoothed / smoothed.sum()


def daily_rate_by_weekday(fct: pd.DataFrame, holidays=HOLIDAYS_2023) -> pd.Series:
    """Average tickets per non-holiday day, by ISO weekday (1 = Mon)."""
    start, end = fct["created_date"].min(), fct["created_date"].max()
    days = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    days = days[~days["date"].isin(pd.to_datetime(holidays))]
    days["dow"] = days["date"].dt.day_of_week + 1
    counts = fct.groupby("created_date").size()
    days["tickets"] = days["date"].map(counts).fillna(0)
    return days.groupby("dow")["tickets"].mean()


def calibration_summary(fct: pd.DataFrame, cfg: dict) -> dict:
    prof = hourly_profile(fct, cfg["scenario"]["hourly_smoothing_weights"])
    rate = daily_rate_by_weekday(fct)
    return {"hourly_profile": prof.tolist(), "daily_rate_by_weekday": rate.round(4).to_dict()}


# ---------------------------------------------------------------------------
# Ticket generation
# ---------------------------------------------------------------------------
def generate_tickets(fct: pd.DataFrame, cfg: dict, rng: np.random.Generator) -> pd.DataFrame:
    """One synthetic year of tickets at `scale_factor` x the real volume."""
    scale = cfg["scenario"]["scale_factor"]
    year = cfg["scenario"]["year"]
    prof = hourly_profile(fct, cfg["scenario"]["hourly_smoothing_weights"])
    rate = daily_rate_by_weekday(fct)
    holidays = set(pd.to_datetime(HOLIDAYS_2023).date)

    # 1) arrivals: non-homogeneous Poisson, rate = scale x weekday rate x hour share
    hours = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    dow = hours.day_of_week + 1
    lam = scale * rate.reindex(dow).to_numpy() * prof[hours.hour]
    lam[np.isin(hours.date, list(holidays))] = 0.0
    n_per_hour = rng.poisson(lam)
    hour_start = np.repeat(hours.to_numpy(), n_per_hour)
    offsets = rng.uniform(0, SECONDS_PER_HOUR, size=len(hour_start))
    created = pd.to_datetime(hour_start) + pd.to_timedelta(offsets, unit="s")
    created = np.sort(created.to_numpy())
    t = pd.DataFrame({"created_at": created})
    t["created_month"] = t["created_at"].dt.to_period("M").dt.to_timestamp()

    # 2) attributes: bootstrap a real ticket created in the same month
    seed_cols = ["ticket_id", "channel", "priority", "topic", "product_group", "agent_group",
                 "support_level", "country", "agent_interactions", "resolution_outcome",
                 "resolution_h", "frt_min", "frt_invalid", "first_response_at", "csat_score",
                 "response_target_min", "resolution_target_h"]
    seed = fct[seed_cols + ["created_month"]].copy()
    seed["created_month"] = pd.to_datetime(seed["created_month"])
    parts = []
    for month, grp in t.groupby("created_month", sort=True):
        pool = seed[seed["created_month"] == month].reset_index(drop=True)
        idx = rng.integers(0, len(pool), size=len(grp))
        draw = pool.iloc[idx].drop(columns="created_month").reset_index(drop=True)
        draw.index = grp.index
        parts.append(draw)
    attrs = pd.concat(parts).sort_index()
    attrs = attrs.rename(columns={"ticket_id": "seed_ticket_id"})
    t = pd.concat([t, attrs], axis=1)

    # 3) repair fields that were invalid in the seed row (documented in DQ checks)
    #    - interactions missing: sentinel 60 (Chat) or untouched Open ticket
    never_touched = t["first_response_at"].isna()          # Open tickets: no agent touch yet
    valid_inter = fct.loc[fct["agent_interactions"].notna(), ["channel", "agent_interactions"]]
    need = t["agent_interactions"].isna() & ~never_touched
    for ch, grp in t[need].groupby("channel"):
        pool = valid_inter.loc[valid_inter["channel"] == ch, "agent_interactions"].to_numpy()
        t.loc[grp.index, "agent_interactions"] = rng.choice(pool, size=len(grp))
    t.loc[never_touched, "agent_interactions"] = 0
    t["agent_interactions"] = t["agent_interactions"].astype(int)
    #    - first response before creation (2 Phone seeds): redraw a valid delay
    bad = t["frt_invalid"].fillna(False).astype(bool)
    for ch, grp in t[bad].groupby("channel"):
        pool = fct.loc[(fct["channel"] == ch) & fct["frt_min"].notna(), "frt_min"].to_numpy()
        t.loc[grp.index, "frt_min"] = rng.choice(pool, size=len(grp))

    # 4) derived timestamps and outcomes
    t["pickup_delay_min"] = t["frt_min"].astype(float)          # NaN = never responded
    resolved = t["resolution_outcome"].str.startswith("Resolved")
    t["resolved_at"] = t["created_at"] + pd.to_timedelta(t["resolution_h"].where(resolved), unit="h")
    t["resolution_sla_met"] = t["resolution_outcome"].eq("Resolved within SLA")
    t["channel_group"] = np.where(t["channel"].isin(LIVE_CHANNELS), "Live (chat/phone)", "Async (email)")
    t["created_dow"] = t["created_at"].dt.day_of_week + 1
    t["created_hour"] = t["created_at"].dt.hour
    t["created_date"] = t["created_at"].dt.floor("D")
    t["ticket_id"] = np.arange(100001, 100001 + len(t))
    t = t.drop(columns=["frt_min", "frt_invalid", "first_response_at"])
    first = ["ticket_id", "seed_ticket_id", "created_at", "created_date", "created_month",
             "created_dow", "created_hour", "channel", "channel_group"]
    return t[first + [c for c in t.columns if c not in first]]


# ---------------------------------------------------------------------------
# Work items: the agent workload each ticket creates
# ---------------------------------------------------------------------------
def _lognormal(rng, mean, cv, size):
    sigma2 = np.log(1 + cv ** 2)
    mu = np.log(mean) - sigma2 / 2
    return rng.lognormal(mu, np.sqrt(sigma2), size)


def follow_up_touches(interactions: np.ndarray, channel: np.ndarray, semantics: str) -> np.ndarray:
    inter = np.asarray(interactions, int)
    if semantics == "touches":
        k = inter - 1
    elif semantics == "half_agent":
        k = np.ceil(inter / 2).astype(int) - 1
    elif semantics == "chat_in_session":
        k = np.where(np.asarray(channel) == "Chat", 0, inter - 1)
    else:
        raise ValueError(f"unknown semantics {semantics!r}")
    return np.clip(k, 0, None)


def build_work_items(tickets: pd.DataFrame, cfg: dict, rng: np.random.Generator,
                     semantics: str = "touches", aht_multiplier: float = 1.0,
                     t0: pd.Timestamp | None = None) -> pd.DataFrame:
    """Translate tickets into agent work items with arrival time and handle time.

    * first touch: chat/phone -> LIVE item at creation (customer is waiting);
      email -> ASYNC item at creation (first reply).
    * follow-up touches -> ASYNC items spread uniformly between 1 hour after creation
      and the ticket's resolution (or 6 days for tickets never resolved).
    Tickets never touched in the seed (Open, no response) create no work.
    Times are seconds from t0 (default: 1 Jan of the scenario year, 00:00).
    """
    st = cfg["staffing"]
    ht = st["handle_time_min"]
    cv = st["handle_time_cv"]
    t0 = t0 or pd.Timestamp(f"{cfg['scenario']['year']}-01-01")
    touched = tickets[tickets["agent_interactions"] > 0]
    created_s = (touched["created_at"] - t0).dt.total_seconds().to_numpy()
    ch = touched["channel"].to_numpy()
    first_mean = np.select([ch == "Chat", ch == "Phone"], [ht["chat_first"], ht["phone_first"]], ht["email_first"])
    first_service = _lognormal(rng, 1.0, cv, len(touched)) * first_mean * 60 * aht_multiplier
    first = pd.DataFrame({
        "ticket_id": touched["ticket_id"].to_numpy(),
        "kind": np.where(np.isin(ch, LIVE_CHANNELS), "live_first", "email_first"),
        "pool": np.where(np.isin(ch, LIVE_CHANNELS), "live", "async"),
        "channel": ch,
        "topic": touched["topic"].to_numpy(),
        "arrival_s": created_s,
        "service_s": first_service,
        "pickup_delay_min": touched["pickup_delay_min"].to_numpy(),
        "response_target_min": touched["response_target_min"].to_numpy(),
    })
    k = follow_up_touches(touched["agent_interactions"].to_numpy(), ch, semantics)
    rep = np.repeat(np.arange(len(touched)), k)
    life_h = np.where(touched["resolution_h"].notna(), touched["resolution_h"].to_numpy(), 144.0)
    life_h = np.maximum(life_h, 2.0)
    lo = created_s[rep] + 3600.0
    hi = created_s[rep] + life_h[rep] * 3600.0
    fu = pd.DataFrame({
        "ticket_id": touched["ticket_id"].to_numpy()[rep],
        "kind": "follow_up",
        "pool": "async",
        "channel": ch[rep],
        "topic": touched["topic"].to_numpy()[rep],
        "arrival_s": rng.uniform(lo, hi),
        "service_s": _lognormal(rng, 1.0, cv, len(rep)) * ht["follow_up"] * 60 * aht_multiplier,
        "pickup_delay_min": np.nan,
        "response_target_min": np.nan,
    })
    items = pd.concat([first, fu], ignore_index=True).sort_values("arrival_s", kind="stable")
    return items.reset_index(drop=True)
