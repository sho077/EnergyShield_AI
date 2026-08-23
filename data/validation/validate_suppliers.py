#!/usr/bin/env python3
"""Validate the supplier / origin country master dataset.

Dataset: data/reference/suppliers.csv
Read-only: this script never modifies the source CSV.

This table is a REFERENCE list of candidate origin countries. It is explicitly
not a ranking, a market-share table, or a live availability feed. The two
checks that matter most therefore both guard against scope creep: no column may
express a volume, share or ranking, and india_supply_relevance may only hold
the single neutral value the dataset is allowed to assert.

It also enforces referential integrity of major_crude_grades against
crude_grades.csv, so a supplier can never cite a grade the project has no
sourced assay record for.

Exit codes: 0 PASS, 1 critical FAIL, 2 dataset unreadable.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "supplier / origin country master"

EXPECTED_COLUMNS = [
    "supplier_id", "country", "iso_alpha3", "un_m49_code", "region", "subregion",
    "major_export_ports", "major_crude_grades", "india_supply_relevance",
    "sanctions_reference_status", "source", "source_url", "report_date",
    "retrieved_at", "notes",
]

REQUIRED_COLUMNS = [
    "supplier_id", "country", "iso_alpha3", "un_m49_code", "region", "subregion",
    "india_supply_relevance", "sanctions_reference_status", "source",
    "source_url", "report_date", "retrieved_at", "notes",
]

NULLABLE_COLUMNS = ["major_export_ports", "major_crude_grades"]

# The ONLY value this reference dataset is permitted to assert. Anything richer
# would be a claim about ranking or availability, which belongs to a later
# dynamic dataset, not here.
ALLOWED_RELEVANCE = {"reference_candidate_origin"}

SANCTIONS_STATUSES = {
    "ofac_country_program_listed",
    "no_ofac_country_program_listed",
    "not_assessed",
}

# UN M49 regions, as published.
UN_REGIONS = {"Africa", "Americas", "Asia", "Europe", "Oceania"}

ISO_ALPHA3 = re.compile(r"^[A-Z]{3}$")
M49_CODE = re.compile(r"^\d{3}$")

EXPECTED_ROW_COUNT = 10


def check_no_market_claims(rep, header, rows):
    """The dataset must not smuggle in volumes, shares or a ranking."""
    rep.section("L. NO VOLUME / SHARE / RANKING CLAIMS")

    forbidden = [h for h in header
                 if any(t in h.lower() for t in
                        ("volume", "share", "percent", "pct", "rank", "barrel",
                         "bbl", "mmt", "tonnes", "price", "availability", "spot"))]
    if forbidden:
        rep.fail("Column(s) expressing a volume, share, ranking or price: {}. "
                 "This is a reference origin list, not a market dataset.".format(forbidden))
    else:
        rep.ok("No volume, share, ranking or price column present")

    # Row ORDER must not be readable as a ranking either.
    unordered = [r["supplier_id"] for r in rows
                 if "rank" in (r.get("notes") or "").lower()
                 and "not" not in (r.get("notes") or "").lower()]
    if unordered:
        rep.warn("Row(s) whose notes mention ranking without negating it: {}".format(
            unordered))
    else:
        rep.ok("No row asserts a supply ranking")


def check_relevance_neutrality(rep, rows):
    rep.section("M. SUPPLY-RELEVANCE NEUTRALITY")
    values = {(r.get("india_supply_relevance") or "").strip() for r in rows}
    bad = values - ALLOWED_RELEVANCE
    if bad:
        rep.fail("india_supply_relevance carries value(s) beyond the single neutral "
                 "value {}: {}".format(sorted(ALLOWED_RELEVANCE), sorted(bad)))
    else:
        rep.ok("india_supply_relevance is uniformly {!r} -- no country is asserted to "
               "be more or less important than another".format(
                   next(iter(ALLOWED_RELEVANCE))))


def check_un_m49(rep, rows):
    """Country identity must be traceable to UN M49, not to a house style."""
    rep.section("N. UN M49 IDENTIFIER INTEGRITY")

    bad_iso = ["{}: {!r}".format(r["supplier_id"], r.get("iso_alpha3"))
               for r in rows if not ISO_ALPHA3.match((r.get("iso_alpha3") or "").strip())]
    if bad_iso:
        rep.fail("iso_alpha3 value(s) not three upper-case letters: {}".format(bad_iso))
    else:
        rep.ok("All iso_alpha3 values are well-formed ISO 3166-1 alpha-3 codes")

    bad_m49 = ["{}: {!r}".format(r["supplier_id"], r.get("un_m49_code"))
               for r in rows if not M49_CODE.match((r.get("un_m49_code") or "").strip())]
    if bad_m49:
        rep.fail("un_m49_code value(s) not exactly three digits: {}".format(bad_m49))
    else:
        rep.ok("All un_m49_code values are three digits, leading zeros preserved")

    leading_zero = [r["supplier_id"] for r in rows
                    if (r.get("un_m49_code") or "").strip().startswith("0")]
    if leading_zero:
        rep.info("{} M49 code(s) rely on a preserved leading zero: {}".format(
            len(leading_zero), leading_zero))

    bad_region = sorted({(r.get("region") or "").strip() for r in rows
                         if (r.get("region") or "").strip() not in UN_REGIONS})
    if bad_region:
        rep.fail("region value(s) outside the UN M49 top-level regions {}: {}".format(
            sorted(UN_REGIONS), bad_region))
    else:
        rep.ok("Every region is a UN M49 top-level region")

    for col in ("iso_alpha3", "un_m49_code", "country"):
        values = [(r.get(col) or "").strip() for r in rows]
        if len(set(values)) != len(values):
            rep.fail("{} values are not unique".format(col))
        else:
            rep.ok("All {} values are unique".format(col))


def check_grade_references(rep, rows):
    known = c.load_reference_ids("crude_grades.csv", "crude_grade_id")
    if known is None:
        rep.section("O. REFERENTIAL INTEGRITY (major_crude_grades)")
        rep.warn("crude_grades.csv not present -- grade references were not checked")
        return
    c.check_foreign_key(rep, rows, "major_crude_grades", known,
                        "crude_grades.csv:crude_grade_id",
                        allow_blank=True, multi_sep=";")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = c.REFERENCE_DIR / "suppliers.csv"
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

    if len(rows) != EXPECTED_ROW_COUNT:
        rep.warn("Row count = {}, the documented initial candidate list has {} "
                 "countries".format(len(rows), EXPECTED_ROW_COUNT))

    c.check_unique_id(rep, rows, "supplier_id", r"^SUP\d{3}$")
    c.check_required(rep, rows, REQUIRED_COLUMNS)
    c.check_nullable(rep, rows, NULLABLE_COLUMNS)
    c.check_provenance(rep, rows, date_columns=("report_date", "retrieved_at"))
    c.check_controlled(rep, rows, {
        "india_supply_relevance": ALLOWED_RELEVANCE,
        "sanctions_reference_status": SANCTIONS_STATUSES,
    })
    c.check_whitespace(rep, rows, header)

    check_no_market_claims(rep, header, rows)
    check_relevance_neutrality(rep, rows)
    check_un_m49(rep, rows)
    check_grade_references(rep, rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
