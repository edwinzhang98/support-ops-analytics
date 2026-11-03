"""Load config.yaml and resolve paths.

The raw data path defaults to the value in config.yaml and can be overridden
with the SUPPORT_TICKETS_CSV environment variable (or a .env file at the repo root).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = REPO_ROOT / "sql"


@lru_cache(maxsize=1)
def load_config(path: str | None = None) -> dict:
    load_dotenv(REPO_ROOT / ".env")
    cfg_path = Path(path) if path else REPO_ROOT / "config.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    raw = os.environ.get("SUPPORT_TICKETS_CSV") or cfg["data"]["raw_csv"]
    cfg["data"]["raw_csv"] = str(Path(os.path.expanduser(raw)))
    cfg["data"]["processed_dir"] = str(REPO_ROOT / cfg["data"]["processed_dir"])
    cfg["reports_dir"] = str(REPO_ROOT / cfg["reports_dir"])
    return cfg


def processed_path(name: str) -> Path:
    """Path of a cached artefact in data/processed (e.g. 'fct_tickets.parquet')."""
    p = Path(load_config()["data"]["processed_dir"])
    p.mkdir(parents=True, exist_ok=True)
    return p / name


def reports_path(*parts: str) -> Path:
    p = Path(load_config()["reports_dir"]).joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
