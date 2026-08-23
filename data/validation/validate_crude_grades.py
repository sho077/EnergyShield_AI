#!/usr/bin/env python3
"""Validate the crude grade master dataset.

Dataset: data/reference/crude_grades.csv
Read-only: this script never modifies the source CSV.

The load-bearing rule here is the point-vs-range discipline. Several producers
publish an assay as a BAND ("32 to 36 API"), not a single figure. Collapsing a
band to its midpoint would manufacture a number no source ever printed, so the
schema keeps point values and published ranges in separate columns and this
validator enforces that a row never carries both for the same property, and
that any row with neither says why in its notes.

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

DATASET = "crude grade master"

EXPECTED_COLUMNS = [
    "crude_grade_id", "crude_grade", "country", "producer", "api_gravity_deg",
    "api_gravity_range_deg", "sulfur_pct", "sulfur_pct_range", "classification",
    "typical_export_region", "source", "source_url", "report_date",
    "retrieved_at", "notes",
]

REQUIRED_COLUMNS = [
    "crude_grade_id", "crude_grade", "country", "source", "source_url",
    "report_date", "retrieved_at", "notes",
]

NULLABLE_COLUMNS = [
    "producer", "api_gravity_deg", "api_gravity_range_deg", "sulfur_pct",
    "sulfur_pct_range", "classification", "typical_export_region",
]

# Physically plausible bounds. API gravity below 0 is possible in principle for
# extreme bitumen but no traded export grade sits there; anything outside this
# band is far likelier to be a transcription error than a real assay.
API_MIN, API_MAX = Decimal("0"), Decimal("60")
SULFUR_MIN, SULFUR_MAX = Decimal("0"), Decimal("10")

PROPERTY_PAIRS = [
    ("api_gravity_deg", "api_gravity_range_deg", API_MIN, API_MAX, "API gravity"),
    ("sulfur_pct", "sulfur_pct_range", SULFUR_MIN, SULFUR_MAX, "sulfur"),
]

# Phrases that make an absent assay an explicit, reasoned null rather than a
# silent gap.
NULL_JUSTIFICATIONS = ("null", "chart", "not state", "no authoritative")


def check_point_vs_range(rep, rows):
    rep.section("L. POINT VALUE vs PUBLISHED RANGE")

    for point_col, range_col, lo, hi, label in PROPERTY_PAIRS:
        both, neither, out_of_range, non_numeric = [], [], [], []

        for row in rows:
            gid = row["crude_grade_id"]
            point = (row.get(point_col) or "").strip()
            rng = (row.get(range_col) or "").strip()

            if point and rng:
                both.append(gid)
            if not point and not rng:
                neither.append(gid)

            if point:
                try:
                    value = Decimal(point)
                except (InvalidOperation, ValueError):
                    non_numeric.append("{}: {!r}".format(gid, point))
                    continue
                if not (lo <= value <= hi):
                    out_of_range.append("{}: {} outside [{}, {}]".format(gid, value, lo, hi))

        if non_numeric:
            rep.fail("{}: non-numeric point value(s): {}".format(label, non_numeric))
        else:
            rep.ok("{}: every point value parses as numeric".format(label))

        if out_of_range:
            rep.fail("{}: value(s) outside the physically plausible band: {}".format(
                label, out_of_range))
        else:
            rep.ok("{}: all point values are within the plausible band [{}, {}]".format(
                label, lo, hi))

        if both:
            rep.fail("{}: row(s) carrying BOTH a point value and a range, which is "
                     "ambiguous: {}".format(label, both))
        else:
            rep.ok("{}: no row carries both a point value and a range".format(label))

        if neither:
            rep.info("{}: {} row(s) with no {} value at all: {}".format(
                label, len(neither), label, neither))

    # A range must actually look like a range, not a smuggled point value.
    malformed = []
    for row in rows:
        for _, range_col, _, _, label in PROPERTY_PAIRS:
            rng = (row.get(range_col) or "").strip()
            if not rng:
                continue
            if not re.search(r"(to|less than|more than|-)", rng, re.I):
                malformed.append("{} {}={!r}".format(row["crude_grade_id"], range_col, rng))
    if malformed:
        rep.fail("Range column(s) not expressing a range: {}".format(malformed))
    else:
        rep.ok("Every populated range column expresses a genuine range")


def check_null_justification(rep, rows):
    """A missing assay must be an explained absence, not an unexplained blank."""
    rep.section("M. JUSTIFIED NULLS")
    unexplained = []
    for row in rows:
        has_api = bool((row.get("api_gravity_deg") or "").strip()
                       or (row.get("api_gravity_range_deg") or "").strip())
        has_sulfur = bool((row.get("sulfur_pct") or "").strip()
                          or (row.get("sulfur_pct_range") or "").strip())
        if has_api and has_sulfur:
            continue
        notes = (row.get("notes") or "").lower()
        if not any(t in notes for t in NULL_JUSTIFICATIONS):
            unexplained.append(row["crude_grade_id"])

    if unexplained:
        rep.fail("Row(s) missing an assay value with no explanation in notes: "
                 "{}".format(unexplained))
    else:
        rep.ok("Every row with a missing assay value explains the absence in notes")


def check_no_synthetic_average(rep, rows):
    rep.section("N. NO SYNTHETIC AVERAGING")
    # Any row whose notes mention a range must also state that no midpoint was
    # created, so a later reader cannot mistake a band for a measured value.
    ranged = [r for r in rows
              if (r.get("api_gravity_range_deg") or "").strip()
              or (r.get("sulfur_pct_range") or "").strip()]
    unwarned = [r["crude_grade_id"] for r in ranged
                if "range" not in (r.get("notes") or "").lower()]
    if unwarned:
        rep.fail("Row(s) with a published range whose notes do not say so: "
                 "{}".format(unwarned))
    else:
        rep.ok("All {} range-valued row(s) declare the range in notes".format(len(ranged)))

    conflicts = [r["crude_grade_id"] for r in rows
                 if "SOURCE CONFLICT" in (r.get("notes") or "")]
    if conflicts:
        rep.warn("Documented source conflict(s) on: {} -- both figures preserved, "
                 "neither averaged".format(conflicts))
    else:
        rep.info("No source conflicts recorded in this dataset")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = c.REFERENCE_DIR / "crude_grades.csv"
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

    c.check_unique_id(rep, rows, "crude_grade_id", r"^CG\d{3}$")
    c.check_required(rep, rows, REQUIRED_COLUMNS)
    c.check_nullable(rep, rows, NULLABLE_COLUMNS)
    c.check_provenance(rep, rows, date_columns=("report_date", "retrieved_at"))
    c.check_unique_text(rep, rows, "crude_grade")
    c.check_whitespace(rep, rows, header)

    check_point_vs_range(rep, rows)
    check_null_justification(rep, rows)
    check_no_synthetic_average(rep, rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
