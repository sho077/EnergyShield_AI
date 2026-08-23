#!/usr/bin/env python3
"""Validate the strategic petroleum reserve dataset.

Dataset: data/reference/strategic_reserves.csv
Read-only: this script never modifies the source CSV.

The headline check is the Phase I capacity reconciliation. PIB/MoPNG state a
Phase I total of 5.33 MMT across Visakhapatnam (1.33), Mangaluru (1.5) and
Padur (2.5); the per-row figures must add up to exactly that. Phase II rows are
reconciled separately against the 6.5 MMT approved under the July 2021 Cabinet
decision, and are never folded into the Phase I total -- those facilities are
approved, not built.

Exit codes: 0 PASS, 1 critical FAIL, 2 dataset unreadable.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "strategic petroleum reserves"

EXPECTED_COLUMNS = [
    "reserve_id", "reserve_name", "operator", "phase", "operational_status",
    "location", "state_or_region", "latitude", "longitude", "capacity_mmt",
    "facility_type", "connected_refinery_or_refineries", "coastal_access",
    "pipeline_access", "commissioned_date", "source", "source_url",
    "report_date", "retrieved_at", "notes",
]

# Columns that must never be blank. latitude/longitude, commissioned_date and
# connected_refinery_or_refineries are deliberately NOT here: no authoritative
# value was published for some rows and a null is the honest record.
REQUIRED_COLUMNS = [
    "reserve_id", "reserve_name", "operator", "phase", "operational_status",
    "location", "state_or_region", "capacity_mmt", "facility_type",
    "coastal_access", "pipeline_access", "source", "source_url",
    "report_date", "retrieved_at", "notes",
]

NULLABLE_COLUMNS = [
    "latitude", "longitude", "connected_refinery_or_refineries", "commissioned_date",
]

YES_NO_UNKNOWN = {"yes", "no", "unknown"}
PHASES = {"Phase I", "Phase II"}
STATUSES = {"commissioned", "approved_not_commissioned", "under_construction"}

# Authoritative totals, PIB PRID 2113233 (20 Mar 2025), corroborated by
# PIB PRID 1739019. Cross-checked against ISPRL's own About Us page.
EXPECTED_PHASE1_TOTAL = Decimal("5.33")
EXPECTED_PHASE2_TOTAL = Decimal("6.5")
EXPECTED_PHASE1_ROWS = 3

# The per-location Phase I split, asserted individually so a future refresh
# cannot reach the right total via wrong components.
EXPECTED_PHASE1_SPLIT = {
    "SPR001": Decimal("1.33"),
    "SPR002": Decimal("1.5"),
    "SPR003": Decimal("2.5"),
}


def check_phase_split(rep, rows):
    rep.section("L. PHASE I PER-LOCATION CROSS-CHECK")
    by_id = {(r.get("reserve_id") or "").strip(): r for r in rows}
    for rid, expected in sorted(EXPECTED_PHASE1_SPLIT.items()):
        row = by_id.get(rid)
        if row is None:
            rep.fail("Phase I record {} is missing".format(rid))
            continue
        actual = Decimal((row.get("capacity_mmt") or "0").strip())
        if actual == expected:
            rep.ok("{} {:<44} {} MMT (matches PIB)".format(
                rid, row.get("reserve_name", "")[:44], actual))
        else:
            rep.fail("{} capacity_mmt = {}, PIB states {}".format(rid, actual, expected))

    phase1 = [r for r in rows if (r.get("phase") or "").strip() == "Phase I"]
    if len(phase1) == EXPECTED_PHASE1_ROWS:
        rep.ok("Phase I row count = {} (matches the three commissioned sites)".format(
            len(phase1)))
    else:
        rep.fail("Phase I row count = {}, expected {}".format(
            len(phase1), EXPECTED_PHASE1_ROWS))


def check_inventory_discipline(rep, rows, header):
    """Storage capacity must never be conflated with inventory or days of cover."""
    rep.section("M. CAPACITY vs INVENTORY DISCIPLINE")

    forbidden = [h for h in header
                 if any(t in h.lower() for t in
                        ("inventory", "fill", "stock_level", "days_of_cover",
                         "days_cover", "utilisation", "utilization"))]
    if forbidden:
        rep.fail("Column(s) implying inventory or days-of-cover are present: {}. "
                 "This table records STORAGE CAPACITY only.".format(forbidden))
    else:
        rep.ok("No inventory / fill-level / days-of-cover column present")

    uncommissioned = [r for r in rows
                      if (r.get("operational_status") or "").strip() != "commissioned"]
    unflagged = [r["reserve_id"] for r in uncommissioned
                 if "NOT COMMISSIONED" not in (r.get("notes") or "")]
    if unflagged:
        rep.fail("Non-commissioned record(s) whose notes do not carry the "
                 "'NOT COMMISSIONED' warning: {}".format(unflagged))
    elif uncommissioned:
        rep.ok("All {} non-commissioned record(s) carry an explicit "
               "'NOT COMMISSIONED' note".format(len(uncommissioned)))

    # Every commissioned row must say what its capacity figure is not.
    missing_caveat = [r["reserve_id"] for r in rows
                      if (r.get("operational_status") or "").strip() == "commissioned"
                      and "not inventory" not in (r.get("notes") or "").lower()]
    if missing_caveat:
        rep.fail("Commissioned record(s) missing the capacity-is-not-inventory "
                 "caveat in notes: {}".format(missing_caveat))
    else:
        rep.ok("Every commissioned record states that capacity is not inventory")


def check_source_conflict(rep):
    rep.section("N. KNOWN SOURCE CONFLICT")
    rep.warn("ISPRL's own About Us page states the Phase I total as '5.03 MMT', "
             "while PIB/MoPNG state 5.33 MMT and publish a per-location split "
             "(1.33 + 1.5 + 2.5) that sums to 5.33. The dataset follows the PIB "
             "split because it is internally consistent and per-location; the "
             "ISPRL figure is recorded in docs/data_sources.md rather than "
             "silently discarded.")
    rep.info("Neither figure was averaged, rounded or reconciled by this project.")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = c.REFERENCE_DIR / "strategic_reserves.csv"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=default_csv)
    args = parser.parse_args()

    if not args.csv.is_file():
        print("  [ERROR] Dataset not found: {}".format(args.csv))
        return 2
    try:
        header, rows, ragged = c.load_rows(args.csv)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("  [ERROR] Could not read dataset: {}".format(exc))
        return 2

    c.banner(DATASET, args.csv, len(rows))
    rep = c.Report(DATASET)
    rep.metric("row_count", len(rows))

    if not c.check_schema(rep, header, ragged, EXPECTED_COLUMNS):
        rep.section("SUMMARY")
        print("  Schema is broken; per-field checks were skipped.")
        return 1

    c.check_unique_id(rep, rows, "reserve_id", r"^SPR\d{3}$")
    c.check_required(rep, rows, REQUIRED_COLUMNS)
    c.check_nullable(rep, rows, NULLABLE_COLUMNS)

    c.check_numeric(rep, rows, "capacity_mmt", minimum=Decimal("0"),
                    expected_total=EXPECTED_PHASE1_TOTAL,
                    subset=("Phase I", lambda r: (r.get("phase") or "").strip() == "Phase I"))
    c.check_numeric(rep, rows, "capacity_mmt", minimum=Decimal("0"),
                    expected_total=EXPECTED_PHASE2_TOTAL,
                    subset=("Phase II", lambda r: (r.get("phase") or "").strip() == "Phase II"))

    c.check_coordinates(rep, rows, allow_blank=True,
                        lat_range=(6, 38), lon_range=(68, 98))  # India bounding box
    c.check_provenance(rep, rows,
                       date_columns=("report_date", "retrieved_at", "commissioned_date"),
                       partial_ok=("commissioned_date",))
    c.check_controlled(rep, rows, {
        "coastal_access": YES_NO_UNKNOWN,
        "pipeline_access": YES_NO_UNKNOWN,
        "phase": PHASES,
        "operational_status": STATUSES,
    })
    c.check_unique_text(rep, rows, "reserve_name")
    c.check_whitespace(rep, rows, header)

    check_phase_split(rep, rows)
    check_inventory_discipline(rep, rows, header)
    check_source_conflict(rep)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
