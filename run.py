"""One command for the whole pipeline: python run.py  (same as `make all` without notebooks).

raw export -> clean (SQL) -> data-quality checks -> KPIs (SQL) -> root cause -> synthetic
scale-up -> staffing model + simulation -> automation -> business case -> key numbers
-> figures -> reports/report.html
"""
import argparse

from support_ops import pipeline, report

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-report", action="store_true", help="only rebuild data/processed and key numbers")
    args = ap.parse_args()
    pipeline.run()
    if not args.skip_report:
        report.build()
