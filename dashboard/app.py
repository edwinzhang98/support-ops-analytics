"""Support Ops Analytics - demo app.

Run from the repo root:  streamlit run dashboard/app.py
Pages follow the story: Overview -> Data & Sanity Checks -> Volume Patterns -> Efficiency & SLA
-> Backlog Diagnosis -> Staffing Model -> Automation Opportunities -> Headcount Business Case.
All pages read the cached outputs of `python run.py` (data/processed/*.parquet).
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))   # so pages can `import components`

st.set_page_config(page_title="Support Ops Analytics", page_icon=":material/support_agent:", layout="wide")

PAGES = Path(__file__).resolve().parent / "pages"
nav = st.navigation([
    st.Page(PAGES / "1_overview.py", title="Overview", icon=":material/space_dashboard:", default=True,
            url_path="overview"),
    st.Page(PAGES / "2_data_sanity.py", title="Data & Sanity Checks", icon=":material/fact_check:",
            url_path="data-and-sanity-checks"),
    st.Page(PAGES / "3_volume.py", title="Volume Patterns", icon=":material/calendar_view_week:",
            url_path="volume-patterns"),
    st.Page(PAGES / "4_efficiency.py", title="Efficiency & SLA", icon=":material/timer:",
            url_path="efficiency-and-sla"),
    st.Page(PAGES / "5_backlog.py", title="Backlog Diagnosis", icon=":material/inbox:",
            url_path="backlog-diagnosis"),
    st.Page(PAGES / "6_staffing.py", title="Staffing Model", icon=":material/groups:",
            url_path="staffing-model"),
    st.Page(PAGES / "7_automation.py", title="Automation Opportunities", icon=":material/smart_toy:",
            url_path="automation-opportunities"),
    st.Page(PAGES / "8_business_case.py", title="Headcount Business Case", icon=":material/request_quote:",
            url_path="headcount-business-case"),
])
with st.sidebar:
    st.caption("Support Operations · SLA, capacity & headcount review · data through 2023-12-30")
nav.run()
