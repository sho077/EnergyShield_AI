#!/usr/bin/env python3
"""Validate the sanctions / compliance reference dataset.

Dataset: data/reference/sanctions.csv
Read-only: this script never modifies the source CSV.

This dataset is a LOOKUP POINTER, not a screening list, and the checks here
exist to keep it that way. Phase 1 deliberately records sanctions AUTHORITIES
and PROGRAM NAMES only. It does not reproduce the OFAC SDN List, the UN
Consolidated List or the EU Consolidated List, because a partial copy of a
screening list is worse than no copy: it looks usable and is silently stale.

So the validator asserts that every row declares itself incomplete, that no row
carries a natural-person identifier, and that nothing in the file reads as a
legal determination.

Exit codes: 0 PASS, 1 critical FAIL, 2 dataset unreadable.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "sanctions / compliance reference"

EXPECTED_COLUMNS = [
    "sanction_record_id", "record_type", "entity_name", "entity_type", "country",
    "authority", "authority_jurisdiction", "program", "status", "effective_date",
    "is_complete_screening_list", "source", "source_url", "retrieved_at", "notes",
]

REQUIRED_COLUMNS = [
    "sanction_record_id", "record_type", "entity_name", "entity_type", "authority",
    "status", "is_complete_screening_list", "source", "source_url", "retrieved_at",
    "notes",
]

NULLABLE_COLUMNS = ["country", "authority_jurisdiction", "program", "effective_date"]

RECORD_TYPES = {"authority", "country_program", "non_country_program_class"}
ENTITY_TYPES = {"sanctions_authority", "sanctions_program", "sanctions_program_class"}
STATUSES = {"active", "listed_as_active_program", "terminated", "not_assessed"}

# Phrases that would turn a lookup pointer into a legal conclusion.
PROHIBITED_DETERMINATIONS = [
    "is prohibited", "is permitted", "is legal", "is illegal", "may not trade",
    "cleared for", "compliant with", "we assess that", "safe to deal",
]


def check_not_a_screening_list(rep, rows):
    rep.section("L. NOT A SCREENING LIST")

    claiming_complete = [r["sanction_record_id"] for r in rows
                         if (r.get("is_complete_screening_list") or "").strip() != "no"]
    if claiming_complete:
        rep.fail("Row(s) not declaring is_complete_screening_list='no': {}. Every row "
                 "in this dataset must declare itself incomplete.".format(claiming_complete))
    else:
        rep.ok("Every row declares is_complete_screening_list='no'")

    # Only authorities and programs belong here -- never designated parties.
    bad_type = [r["sanction_record_id"] for r in rows
                if (r.get("entity_type") or "").strip() not in ENTITY_TYPES]
    if bad_type:
        rep.fail("Row(s) whose entity_type is not an authority or program: {}. "
                 "Designated persons and entities must NOT be stored here.".format(bad_type))
    else:
        rep.ok("Every row is an authority or a program -- no designated party is stored")

    # A row carrying a person-identifier column would be a red flag.
    rep.info("Reminder: screening must be run against the authority's own current "
             "list at the time of the transaction, never against this file.")


def check_no_person_identifiers(rep, header, rows):
    rep.section("M. NO NATURAL-PERSON IDENTIFIERS")
    forbidden = [h for h in header
                 if any(t in h.lower() for t in
                        ("date_of_birth", "dob", "passport", "national_id", "address",
                         "place_of_birth", "alias", "nationality", "given_name"))]
    if forbidden:
        rep.fail("Column(s) capable of holding natural-person identifiers: {}".format(
            forbidden))
    else:
        rep.ok("No column can hold a natural-person identifier")


def check_no_legal_determination(rep, rows):
    rep.section("N. NO LEGAL DETERMINATIONS")
    offenders = []
    for row in rows:
        blob = " ".join((row.get(col) or "") for col in
                        ("entity_name", "program", "status", "notes")).lower()
        for phrase in PROHIBITED_DETERMINATIONS:
            if phrase in blob:
                offenders.append("{}: {!r}".format(row["sanction_record_id"], phrase))
    if offenders:
        rep.fail("Row(s) reading as a legal determination rather than a lookup "
                 "pointer: {}".format(offenders))
    else:
        rep.ok("No row states a compliance or legal conclusion")


def check_caveat_record(rep, rows):
    """The thematic-programs caveat must exist, or suppliers.csv is misleading."""
    rep.section("O. THEMATIC-PROGRAM CAVEAT")
    caveat = [r for r in rows
              if (r.get("record_type") or "").strip() == "non_country_program_class"]
    if not caveat:
        rep.fail("No 'non_country_program_class' record present. Without it, the "
                 "'no_ofac_country_program_listed' value in suppliers.csv can be "
                 "misread as 'no sanctions exposure'.")
        return
    unwarned = [r["sanction_record_id"] for r in caveat
                if "NEVER be read as" not in (r.get("notes") or "")]
    if unwarned:
        rep.fail("Thematic-program record(s) not spelling out the suppliers.csv "
                 "limitation: {}".format(unwarned))
    else:
        rep.ok("The thematic-program caveat record is present and states the "
               "suppliers.csv limitation explicitly")


def check_authority_coverage(rep, rows):
    rep.section("P. AUTHORITY COVERAGE")
    authorities = {(r.get("authority") or "").strip() for r in rows
                   if (r.get("record_type") or "").strip() == "authority"}
    expected = {
        "U.S. Department of the Treasury",
        "United Nations Security Council",
        "Council of the European Union / European Commission",
    }
    missing = expected - authorities
    if missing:
        rep.warn("Sanctions authority pointer(s) not recorded: {}".format(sorted(missing)))
    else:
        rep.ok("All {} expected sanctions authorities are recorded as pointers".format(
            len(expected)))

    # Every country program must name a country that exists in suppliers.csv,
    # otherwise the lookup cannot be joined to anything.
    known = c.load_reference_ids("suppliers.csv", "country")
    if known is None:
        rep.warn("suppliers.csv not present -- country linkage was not checked")
        return
    orphan = [r["sanction_record_id"] for r in rows
              if (r.get("record_type") or "").strip() == "country_program"
              and (r.get("country") or "").strip() not in known]
    if orphan:
        rep.warn("Country program(s) naming a country absent from suppliers.csv: {} "
                 "-- retained, but they cannot be joined to a supplier row".format(orphan))
    else:
        rep.ok("Every country program joins to a country in suppliers.csv")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = c.REFERENCE_DIR / "sanctions.csv"
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

    c.check_unique_id(rep, rows, "sanction_record_id", r"^SAN\d{3}$")
    c.check_required(rep, rows, REQUIRED_COLUMNS)
    c.check_nullable(rep, rows, NULLABLE_COLUMNS)
    c.check_provenance(rep, rows, date_columns=("effective_date", "retrieved_at"))
    c.check_controlled(rep, rows, {
        "record_type": RECORD_TYPES,
        "entity_type": ENTITY_TYPES,
        "status": STATUSES,
        "is_complete_screening_list": {"no"},
    })
    c.check_unique_text(rep, rows, "entity_name")
    c.check_whitespace(rep, rows, header)

    check_not_a_screening_list(rep, rows)
    check_no_person_identifiers(rep, header, rows)
    check_no_legal_determination(rep, rows)
    check_caveat_record(rep, rows)
    check_authority_coverage(rep, rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
