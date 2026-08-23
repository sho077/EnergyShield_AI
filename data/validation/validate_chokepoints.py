#!/usr/bin/env python3
"""Validate the global oil chokepoint dataset.

Dataset: data/reference/chokepoints.csv
Read-only: this script never modifies the source CSV.

Three rules carry the weight here:

1. No risk scoring. This is a baseline reference table. Any column expressing
   current risk, threat or status is rejected outright, so a later dynamic
   risk layer cannot quietly leak into the reference layer.
2. Every flow figure must state its period and its basis. A bare "20 million
   b/d" with no year and no commodity definition is not a usable baseline, and
   partial-year periods must be visibly partial.
3. Flow is not capacity. A row whose flow figure is really a nameplate
   capacity would silently overstate observed movement, so any row mentioning
   capacity must say explicitly which quantity it stored.

Exit codes: 0 PASS, 1 critical FAIL, 2 dataset unreadable.
"""

from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "global oil chokepoints"

EXPECTED_COLUMNS = [
    "chokepoint_id", "name", "type", "latitude", "longitude",
    "coordinate_source", "coordinate_source_url", "strategic_role",
    "alternative_exists", "alternative_description", "baseline_oil_flow_mbd",
    "flow_basis", "flow_period", "flow_data_origin", "source", "source_url",
    "report_date", "retrieved_at", "notes",
]

REQUIRED_COLUMNS = [
    "chokepoint_id", "name", "type", "strategic_role", "alternative_exists",
    "alternative_description", "source", "source_url", "report_date",
    "retrieved_at", "notes",
]

NULLABLE_COLUMNS = [
    "latitude", "longitude", "coordinate_source", "coordinate_source_url",
    "baseline_oil_flow_mbd", "flow_basis", "flow_period", "flow_data_origin",
]

CHOKEPOINT_TYPES = {"strait", "canal", "pipeline", "cape"}
ALTERNATIVE_VALUES = {"yes", "no", "partial", "unknown", "not_applicable"}

# The brief's minimum set. Absence of any of these is a critical failure.
REQUIRED_CHOKEPOINTS = [
    "Strait of Hormuz",
    "Bab el-Mandeb Strait",
    "Suez Canal",
    "SUMED Pipeline",
    "Strait of Malacca",
    "Turkish Straits",
    "Cape of Good Hope",
]

# A flow period is either a plain year, or an explicit partial range.
FULL_YEAR = re.compile(r"^\d{4}$")
PARTIAL_PERIOD = re.compile(r"^\d{4}-\d{2}/\d{4}-\d{2}$")

MAX_PLAUSIBLE_MBD = Decimal("120")  # well above total world liquids supply


def check_no_risk_scoring(rep, header, rows):
    rep.section("L. NO RISK SCORING IN THE REFERENCE LAYER")
    forbidden = [h for h in header
                 if any(t in h.lower() for t in
                        ("risk", "threat", "score", "severity", "status",
                         "disrupt", "closure_prob", "current"))]
    if forbidden:
        rep.fail("Column(s) expressing current risk or status: {}. Baseline flows and "
                 "dynamic risk must stay in separate layers.".format(forbidden))
    else:
        rep.ok("No risk_score, threat or current-status column present")

    # Rows must not smuggle a standing geopolitical judgement into notes either.
    permanent_claims = []
    for row in rows:
        notes = (row.get("notes") or "").lower()
        role = (row.get("strategic_role") or "").lower()
        for phrase in ("currently blocked", "is unsafe", "permanently closed",
                       "high risk", "will be closed"):
            if phrase in notes or phrase in role:
                permanent_claims.append("{}: {!r}".format(row["chokepoint_id"], phrase))
    if permanent_claims:
        rep.fail("Row(s) stating current geopolitical risk as a standing fact: "
                 "{}".format(permanent_claims))
    else:
        rep.ok("No row states a current geopolitical condition as a permanent fact")


def check_flow_integrity(rep, rows):
    rep.section("M. FLOW FIGURE INTEGRITY")
    bad_value, missing_context, bad_period, partial = [], [], [], []

    for row in rows:
        cid = row["chokepoint_id"]
        raw = (row.get("baseline_oil_flow_mbd") or "").strip()
        basis = (row.get("flow_basis") or "").strip()
        period = (row.get("flow_period") or "").strip()
        origin = (row.get("flow_data_origin") or "").strip()

        if not raw:
            # A null flow is fine, but then every flow-context column must also
            # be null -- context without a value is a half-populated record.
            if basis or period or origin:
                missing_context.append(
                    "{}: flow is null but flow context columns are populated".format(cid))
            continue

        try:
            value = Decimal(raw)
        except (InvalidOperation, ValueError):
            bad_value.append("{}: {!r}".format(cid, raw))
            continue
        if value < 0:
            bad_value.append("{}: negative flow {}".format(cid, value))
        if value > MAX_PLAUSIBLE_MBD:
            bad_value.append("{}: implausible flow {} mb/d".format(cid, value))

        if not basis:
            missing_context.append("{}: flow value with no flow_basis".format(cid))
        if not origin:
            missing_context.append("{}: flow value with no flow_data_origin".format(cid))
        if not period:
            missing_context.append("{}: flow value with no flow_period".format(cid))
        elif FULL_YEAR.match(period):
            pass
        elif PARTIAL_PERIOD.match(period):
            partial.append(cid)
        else:
            bad_period.append("{}: {!r}".format(cid, period))

    if bad_value:
        rep.fail("Invalid flow value(s): {}".format(bad_value))
    else:
        rep.ok("All populated flow values are numeric, non-negative and plausible")

    if missing_context:
        rep.fail("Flow context problem(s): {}".format(missing_context))
    else:
        rep.ok("Every flow figure states its basis, period and data origin")

    if bad_period:
        rep.fail("flow_period value(s) neither a plain year nor an explicit "
                 "YYYY-MM/YYYY-MM partial range: {}".format(bad_period))
    else:
        rep.ok("Every flow_period is an unambiguous year or explicit partial range")

    if partial:
        rep.info("{} chokepoint(s) report a PARTIAL-year period and must not be "
                 "compared with full-year figures: {}".format(len(partial), partial))

    nulls = [r["chokepoint_id"] for r in rows
             if not (r.get("baseline_oil_flow_mbd") or "").strip()]
    if nulls:
        rep.info("{} chokepoint(s) with a null flow -- an unavailable figure, NOT a "
                 "zero: {}".format(len(nulls), nulls))


def check_flow_not_capacity(rep, rows):
    rep.section("N. FLOW IS NOT CAPACITY")
    ambiguous = []
    for row in rows:
        notes = (row.get("notes") or "")
        if "capacit" not in notes.lower():
            continue
        # If a row talks about capacity at all, it must say which it stored.
        if not re.search(r"(THROUGHPUT|not capacity|NOT stored in the flow|"
                         r"capacity and flow are different)", notes, re.I):
            ambiguous.append(row["chokepoint_id"])
    if ambiguous:
        rep.fail("Row(s) mentioning capacity without stating whether the stored flow "
                 "figure is throughput or capacity: {}".format(ambiguous))
    else:
        rep.ok("Every row mentioning capacity distinguishes it from stored throughput")


def check_required_chokepoints(rep, rows):
    rep.section("O. REQUIRED CHOKEPOINT COVERAGE")
    present = {(r.get("name") or "").strip() for r in rows}
    missing = [n for n in REQUIRED_CHOKEPOINTS if n not in present]
    if missing:
        rep.fail("Required chokepoint(s) absent from the dataset: {}".format(missing))
    else:
        rep.ok("All {} required chokepoints are present".format(len(REQUIRED_CHOKEPOINTS)))

    stale = [r["chokepoint_id"] for r in rows if "STALENESS WARNING" in (r.get("notes") or "")]
    if stale:
        rep.warn("{} chokepoint(s) carry a documented staleness warning on their flow "
                 "baseline: {}".format(len(stale), stale))


def check_coordinate_provenance(rep, rows):
    rep.section("P. COORDINATE PROVENANCE")
    unattributed = [r["chokepoint_id"] for r in rows
                    if (r.get("latitude") or "").strip()
                    and not ((r.get("coordinate_source") or "").strip()
                             and (r.get("coordinate_source_url") or "").strip())]
    if unattributed:
        rep.fail("Coordinate(s) with no coordinate_source/coordinate_source_url: "
                 "{}".format(unattributed))
    else:
        rep.ok("Every populated coordinate carries its own separate provenance")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = c.REFERENCE_DIR / "chokepoints.csv"
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

    c.check_unique_id(rep, rows, "chokepoint_id", r"^CP\d{3}$")
    c.check_required(rep, rows, REQUIRED_COLUMNS)
    c.check_nullable(rep, rows, NULLABLE_COLUMNS)
    c.check_coordinates(rep, rows, allow_blank=True)  # global: full lat/lon range
    c.check_provenance(rep, rows, date_columns=("report_date", "retrieved_at"))
    c.check_controlled(rep, rows, {
        "type": CHOKEPOINT_TYPES,
        "alternative_exists": ALTERNATIVE_VALUES,
    })
    c.check_unique_text(rep, rows, "name")
    c.check_whitespace(rep, rows, header)

    check_no_risk_scoring(rep, header, rows)
    check_flow_integrity(rep, rows)
    check_flow_not_capacity(rep, rows)
    check_required_chokepoints(rep, rows)
    check_coordinate_provenance(rep, rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
