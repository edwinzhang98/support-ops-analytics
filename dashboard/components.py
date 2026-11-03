"""Shared building blocks for every dashboard page: cached data loading, page header,
data-source badges, KPI tiles, chart wrapper and the "How to read this" box.

Pages only read cached parquet files written by `python run.py`; nothing is recomputed
on load except the what-if calculations behind the sliders (support_ops.interactive).
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from support_ops.config import load_config, processed_path, reports_path

BADGES = {
    "REAL": ("#e8f1fc", "#184f95", "REAL DATA · 2023 export, 2,330 tickets"),
    "SYNTHETIC": ("#fdeee7", "#9a3a12", "SYNTHETIC · 20x scale-up calibrated to the export"),
    "ASSUMPTION": ("#f0efec", "#52514e", "ASSUMPTIONS · set in config.yaml, adjustable here"),
}

_CSS = """
<style>
  .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px;}
  h1 {font-size: 1.75rem !important; font-weight: 650 !important; margin-bottom: 0.2rem !important;}
  .page-question {font-size: 1.05rem; color: #1f1f1d; margin: 0.25rem 0 0.6rem 0;}
  .badge {display: inline-block; padding: 2px 9px; margin: 0 6px 6px 0; border-radius: 4px;
          font-size: 0.74rem; font-weight: 600; letter-spacing: 0.02em;}
  .takeaway {border-left: 3px solid #2a78d6; padding: 0.35rem 0.8rem; margin: 0.4rem 0 1rem 0;
             background: #f6f9fe; color: #1f1f1d;}
  .muted {color: #6b6a65; font-size: 0.86rem;}
  div[data-testid="stMetric"] {background: #f6f6f4; border-radius: 6px; padding: 0.6rem 0.8rem;}
  div[data-testid="stMetricLabel"] p {font-size: 0.82rem; color: #52514e;}
</style>
"""


def _equal_height_metrics() -> None:
    """KPI tiles in one row get the same height whether or not they show a delta (st.metric height="stretch")."""
    import streamlit.delta_generator as dg
    if getattr(dg.DeltaGenerator.metric, "_equal_height", False):
        return
    original = dg.DeltaGenerator.metric

    def metric(self, *args, **kwargs):
        kwargs.setdefault("height", "stretch")
        return original(self, *args, **kwargs)

    metric._equal_height = True
    dg.DeltaGenerator.metric = metric


def setup_page() -> None:
    _equal_height_metrics()
    st.markdown(_CSS, unsafe_allow_html=True)
    if not processed_path("fct_tickets.parquet").exists():
        st.error("Processed data not found. Run `python run.py` (or `make all`) from the repo root first.")
        st.stop()


@st.cache_data(show_spinner=False)
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(processed_path(f"{name}.parquet"))


@st.cache_data(show_spinner=False)
def key_numbers() -> dict:
    with open(reports_path("key_numbers.json")) as fh:
        return json.load(fh)


@st.cache_data(show_spinner=False)
def config() -> dict:
    return load_config()


def badges(*kinds: str) -> None:
    html = "".join(f"<span class='badge' style='background:{BADGES[k][0]};color:{BADGES[k][1]}'>{BADGES[k][2]}</span>"
                   for k in kinds)
    st.markdown(html, unsafe_allow_html=True)


def page_header(title: str, question: str, *sources: str) -> None:
    """Top of every page: title, the one question this page answers, data-source badges."""
    setup_page()
    st.title(title)
    st.markdown(f"<div class='page-question'><b>This page answers:</b> {question}</div>", unsafe_allow_html=True)
    if sources:
        badges(*sources)


def takeaway(text: str) -> None:
    st.markdown(f"<div class='takeaway'>{text}</div>", unsafe_allow_html=True)


def show(fig, key: str | None = None) -> None:
    """Plotly chart with the project's own styling (not Streamlit's theme), hover enabled."""
    st.plotly_chart(fig, width="stretch", theme=None, key=key,
                    config={"displayModeBar": False, "responsive": True})


def how_to_read(markdown_text: str) -> None:
    """Plain-language explanation at the bottom of each page."""
    st.divider()
    with st.expander("How to read this", expanded=False):
        st.markdown(markdown_text)


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%"


def pp(x: float, d: int = 1) -> str:
    return f"{x:+.{d}f} pts"
