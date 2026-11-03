"""Regenerate the README screenshots of every dashboard page (docs/img/NN_<page>.png).

Needs: pip install -r requirements-dev.txt && python -m playwright install chromium
Run from the repo root: python scripts/take_screenshots.py
Starts Streamlit on a free port, opens each page in headless Chromium, waits for the charts,
and saves a full-page screenshot.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
PAGES = [
    ("", "01_overview"), ("data-and-sanity-checks", "02_data_sanity"),
    ("volume-patterns", "03_volume"), ("efficiency-and-sla", "04_efficiency"),
    ("backlog-diagnosis", "05_backlog"), ("staffing-model", "06_staffing"),
    ("automation-opportunities", "07_automation"), ("headcount-business-case", "08_business_case"),
]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.port",
                             str(port), "--server.headless", "true"], cwd=ROOT,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
            for _ in range(60):
                try:
                    page.goto(base, timeout=2000)
                    break
                except Exception:
                    time.sleep(1)
            t_first = None
            for path, name in PAGES:
                t0 = time.time()
                page.goto(f"{base}/{path}", wait_until="networkidle")
                page.wait_for_selector("h1", timeout=30000)
                page.wait_for_selector(".js-plotly-plot", timeout=30000)
                page.wait_for_timeout(1500)
                if t_first is None:
                    t_first = time.time() - t0
                # Streamlit scrolls inside its main container, so grow the viewport to the content height
                h = page.evaluate("""() => { const m = document.querySelector('section.stMain, [data-testid="stMain"]');
                                             return m ? m.scrollHeight : document.body.scrollHeight; }""")
                page.set_viewport_size({"width": 1440, "height": int(min(max(h, 900), 12000))})
                page.wait_for_timeout(1200)
                page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
                page.set_viewport_size({"width": 1440, "height": 900})
                print(f"saved {name}.png ({time.time() - t0:.1f}s)")
            browser.close()
        print(f"first page rendered in {t_first:.1f}s")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
