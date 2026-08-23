"""Loads EnergyShield-AI reference/processed CSVs. Reads only — never mutates source data."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "data" / "reference"
PROC = ROOT / "data" / "processed"


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


@st.cache_data(show_spinner=False)
def load_all() -> dict[str, pd.DataFrame]:
    data = {
        "refineries": _read(REF / "refineries.csv"),
        "ports": _read(REF / "ports.csv"),
        "pipelines": _read(REF / "pipelines.csv"),
        "reserves": _read(REF / "strategic_reserves.csv"),
        "network_links": _read(REF / "network_links.csv"),
        "chokepoints": _read(REF / "chokepoints.csv"),
        "routes": _read(REF / "routes.csv"),
        "route_nodes": _read(REF / "route_nodes.csv"),
        "suppliers": _read(REF / "suppliers.csv"),
        "crude_grades": _read(REF / "crude_grades.csv"),
        "sanctions": _read(REF / "sanctions.csv"),
        "source_registry": _read(REF / "source_registry.csv"),
        "energy_prices": _read(REF / "energy_prices_reference.csv"),
        "computed_routes": _read(PROC / "computed_routes.csv"),
        "route_segments": _read(PROC / "route_segments.csv"),
    }
    for key in ("refineries",):
        if "capacity_mmtpa" in data[key].columns:
            data[key]["capacity_mmtpa_num"] = pd.to_numeric(
                data[key]["capacity_mmtpa"], errors="coerce"
            )
    if "capacity_mmt" in data["reserves"].columns:
        data["reserves"]["capacity_mmt_num"] = pd.to_numeric(
            data["reserves"]["capacity_mmt"], errors="coerce"
        )
    return data
