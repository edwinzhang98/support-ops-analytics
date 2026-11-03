"""Discrete-event simulation of the support queue under a given roster.

Why simulate when Erlang C exists? Erlang C treats every hour as a separate,
steady-state world. In reality a backlog built at 15:00 is still there at 16:00,
handle times are not exponential, and live chats/calls jump ahead of email work.
The simulation replays the synthetic year ticket by ticket and measures what each
roster actually delivers.

Model
  * One blended pool of agents; the number on duty changes every hour (roster x
    (1 - shrinkage), fractional values sampled per hour, see productive_servers).
  * LIVE items (chat/phone first contact) have preemptive-resume priority: if all
    agents are busy and one is doing async work, that work is paused and goes back
    to the front of the async queue. Agents start their shift fresh; an agent whose
    shift ends finishes the item in hand first.
  * ASYNC items (email first replies, follow-up touches) are served first-come-first-served.
  * Output: the time each item first reaches an agent (wait = start - arrival).

simulate_fcfs() is a plain FCFS multi-server queue with time-varying servers,
used to validate the simulation against Erlang C (tests/test_simulation.py).
"""
from __future__ import annotations

import heapq
import math
from collections import deque

import numpy as np
import pandas as pd

INF = math.inf


def productive_servers(scheduled_by_hour: np.ndarray, shrinkage: float,
                       rng: np.random.Generator) -> np.ndarray:
    """Agents actually available each hour: scheduled x (1 - shrinkage).

    A fractional value p (e.g. 6.3) becomes floor(p) or floor(p)+1 at random with
    the right average - the way breaks and absences make availability lumpy.
    """
    p = np.asarray(scheduled_by_hour, float) * (1.0 - shrinkage)
    base = np.floor(p)
    return (base + (rng.random(len(p)) < (p - base))).astype(int)


def simulate_fcfs(arrival_s, service_s, servers_by_hour, interval_s: float = 3600.0) -> np.ndarray:
    """FCFS multi-server queue with a time-varying number of servers. Returns start times."""
    arr = np.asarray(arrival_s, float)
    order = np.argsort(arr, kind="stable")
    a = arr[order].tolist()
    s = np.asarray(service_s, float)[order].tolist()
    caps = [int(x) for x in servers_by_hour]
    n, H = len(a), len(caps)
    start = [INF] * n
    comp: list[float] = []
    q: deque[int] = deque()
    on_duty = idle = to_remove = 0
    i = h = 0
    while True:
        t_arr = a[i] if i < n else INF
        t_comp = comp[0] if comp else INF
        t_bnd = h * interval_s if h < H else INF
        if t_arr == INF and t_comp == INF and (t_bnd == INF or not q):
            break
        if t_comp <= t_bnd and t_comp <= t_arr:
            heapq.heappop(comp)
            if to_remove > 0:
                to_remove -= 1
                on_duty -= 1
            elif q:
                j = q.popleft()
                start[j] = t_comp
                heapq.heappush(comp, t_comp + s[j])
            else:
                idle += 1
        elif t_bnd <= t_arr:
            target = caps[h]
            h += 1
            eff = on_duty - to_remove
            if target > eff:
                add = target - eff
                cancel = min(to_remove, add)
                to_remove -= cancel
                add -= cancel
                on_duty += add
                idle += add
                while idle > 0 and q:
                    j = q.popleft()
                    start[j] = t_bnd
                    heapq.heappush(comp, t_bnd + s[j])
                    idle -= 1
            elif target < eff:
                remove = eff - target
                r_idle = min(idle, remove)
                idle -= r_idle
                on_duty -= r_idle
                to_remove += remove - r_idle
        else:
            j = i
            i += 1
            if idle > 0:
                idle -= 1
                start[j] = t_arr
                heapq.heappush(comp, t_arr + s[j])
            else:
                q.append(j)
    out = np.empty(n)
    out[order] = start
    return out


def simulate_blended(arrival_s, service_s, is_live, servers_by_hour,
                     interval_s: float = 3600.0) -> dict[str, np.ndarray]:
    """Blended pool, live work preempts async work (preemptive-resume).

    Returns dict with 'start' (first time each item reached an agent), 'finish',
    and 'queue_len' (items waiting at each hour boundary, live + async).
    """
    arr = np.asarray(arrival_s, float)
    order = np.argsort(arr, kind="stable")
    a = arr[order].tolist()
    remaining = np.asarray(service_s, float)[order].tolist()
    live = np.asarray(is_live, bool)[order].tolist()
    caps = [int(x) for x in servers_by_hour]
    n, H = len(a), len(caps)
    start = [INF] * n
    finish = [INF] * n
    queue_len = np.zeros(H, dtype=np.int32)

    # agent state (agents are created on demand and reused)
    job: list[int] = []          # item index, -1 if idle / off duty
    seg_start: list[float] = []  # when the current service segment began
    version: list[int] = []      # invalidates stale completion events after preemption
    leaving: list[bool] = []
    idle_agents: list[int] = []  # on duty and idle (stack)
    off_agents: list[int] = []   # off duty (reusable)
    async_agents: set[int] = set()
    busy_count = 0               # on-duty agents currently serving (incl. leaving)
    comp: list[tuple[float, int, int]] = []
    live_q: deque[int] = deque()
    async_q: deque[int] = deque()

    def begin(ag: int, j: int, t: float) -> None:
        nonlocal busy_count
        job[ag] = j
        seg_start[ag] = t
        version[ag] += 1
        busy_count += 1
        if start[j] == INF:
            start[j] = t
        if not live[j]:
            async_agents.add(ag)
        heapq.heappush(comp, (t + remaining[j], ag, version[ag]))

    def next_work(ag: int, t: float) -> None:
        """Agent `ag` is free at t: take live work first, then async, else go idle."""
        if live_q:
            begin(ag, live_q.popleft(), t)
        elif async_q:
            begin(ag, async_q.popleft(), t)
        else:
            idle_agents.append(ag)

    def new_agent() -> int:
        if off_agents:
            return off_agents.pop()
        job.append(-1)
        seg_start.append(0.0)
        version.append(0)
        leaving.append(False)
        return len(job) - 1

    i = h = 0
    while True:
        t_arr = a[i] if i < n else INF
        t_comp = comp[0][0] if comp else INF
        t_bnd = h * interval_s if h < H else INF
        if t_arr == INF and t_comp == INF and (t_bnd == INF or not (live_q or async_q)):
            break
        if t_comp <= t_bnd and t_comp <= t_arr:
            t, ag, ver = heapq.heappop(comp)
            if ver != version[ag] or job[ag] < 0:
                continue                     # stale event (agent was preempted)
            j = job[ag]
            finish[j] = t
            remaining[j] = 0.0
            job[ag] = -1
            busy_count -= 1
            async_agents.discard(ag)
            if leaving[ag]:
                leaving[ag] = False
                off_agents.append(ag)
            else:
                next_work(ag, t)
        elif t_bnd <= t_arr:
            t = t_bnd
            queue_len[h] = len(live_q) + len(async_q)
            target = caps[h]
            h += 1
            n_leaving = sum(1 for ag in range(len(job)) if leaving[ag])
            on_duty_effective = len(idle_agents) + busy_count - n_leaving
            if target > on_duty_effective:
                add = target - on_duty_effective
                for ag in range(len(job)):        # first cancel pending departures
                    if add == 0:
                        break
                    if leaving[ag]:
                        leaving[ag] = False
                        add -= 1
                for _ in range(add):
                    next_work(new_agent(), t)
            elif target < on_duty_effective:
                remove = on_duty_effective - target
                while remove and idle_agents:
                    off_agents.append(idle_agents.pop())
                    remove -= 1
                if remove:                        # busy agents finish their item, then leave
                    for ag in sorted(range(len(job)), key=lambda x: (x not in async_agents, x)):
                        if remove == 0:
                            break
                        if job[ag] >= 0 and not leaving[ag]:
                            leaving[ag] = True
                            remove -= 1
        else:
            j = i
            i += 1
            t = t_arr
            if idle_agents:
                begin(idle_agents.pop(), j, t)
            elif live[j] and async_agents:
                staying = [a for a in async_agents if not leaving[a]]
                ag = min(staying) if staying else min(async_agents)   # preempt an agent doing async work
                k = job[ag]
                remaining[k] -= t - seg_start[ag]
                async_q.appendleft(k)
                async_agents.discard(ag)
                busy_count -= 1
                begin(ag, j, t)
            elif live[j]:
                live_q.append(j)
            else:
                async_q.append(j)

    out_start = np.empty(n)
    out_finish = np.empty(n)
    out_start[order] = start
    out_finish[order] = finish
    return {"start": out_start, "finish": out_finish, "queue_len": queue_len}


# ---------------------------------------------------------------------------
# Scenario wrapper: weekly roster -> simulated year -> SLA summary
# ---------------------------------------------------------------------------
def hour_of_week_index(t0: pd.Timestamp, n_hours: int) -> np.ndarray:
    """Hour-of-week (Mon 00:00 = 0 ... Sun 23:00 = 167) for each hour from t0."""
    first = t0.day_of_week * 24 + t0.hour
    return (first + np.arange(n_hours)) % 168


def run_roster(items: pd.DataFrame, roster_by_how: np.ndarray, shrinkage: float,
               rng: np.random.Generator, t0: pd.Timestamp, n_hours: int) -> dict:
    """Simulate one weekly roster (168 scheduled-agent values, Mon 00 = index 0) over the horizon."""
    how = hour_of_week_index(t0, n_hours)
    scheduled = np.asarray(roster_by_how, float)[how]
    servers = productive_servers(scheduled, shrinkage, rng)
    res = simulate_blended(items["arrival_s"].to_numpy(), items["service_s"].to_numpy(),
                           (items["pool"] == "live").to_numpy(), servers)
    wait_s = res["start"] - items["arrival_s"].to_numpy()
    busy_s = float(np.sum(items["service_s"].to_numpy()[np.isfinite(res["finish"])]))
    return {"wait_s": wait_s, "servers": servers, "scheduled": scheduled,
            "queue_len": res["queue_len"], "utilisation": busy_s / max(servers.sum() * 3600.0, 1.0)}


def summarize_response(items: pd.DataFrame, wait_s: np.ndarray,
                       tickets: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per-ticket response outcome.

    queue_wait_min : time the first touch waited for a free agent (staffing component)
    pickup_delay   : the real first-response delay of the bootstrapped seed ticket. At the
                     export's volume nobody queues, so this measures how fast agents pick
                     work up when they are free (process component)
    response_min   : the LATER of the two (optimistic bound: waiting for an agent and slow pickup
                     overlap, so a ticket is on time if an agent was free in time AND it was
                     picked up in time). response_met_sum uses the SUM (conservative bound: the
                     two delays add up). The export's on-time response times are spread evenly
                     inside the target window, so the sum rule pushes many of them over the line;
                     the truth lies between the two.
    Tickets never touched in the seed (still Open, no response) count as breached.
    """
    first = items["kind"].isin(["live_first", "email_first"]).to_numpy()
    df = items.loc[first, ["ticket_id", "channel", "arrival_s", "pickup_delay_min", "response_target_min"]].copy()
    df["queue_wait_min"] = wait_s[first] / 60.0
    if tickets is not None:
        missing = tickets.loc[~tickets["ticket_id"].isin(df["ticket_id"]),
                              ["ticket_id", "channel", "response_target_min"]].copy()
        missing["arrival_s"] = np.nan
        missing["pickup_delay_min"] = np.nan
        missing["queue_wait_min"] = 0.0
        df = pd.concat([df, missing], ignore_index=True)
    pickup = df["pickup_delay_min"].fillna(np.inf)
    df["queue_met"] = df["queue_wait_min"] <= df["response_target_min"]
    df["process_met"] = pickup <= df["response_target_min"]
    df["response_min"] = np.maximum(pickup, df["queue_wait_min"])          # optimistic bound
    df["response_met"] = df["response_min"] <= df["response_target_min"]
    df["response_met_sum"] = (pickup + df["queue_wait_min"]) <= df["response_target_min"]   # conservative bound
    return df
