#!/usr/bin/env python3
"""Validate the refinery master dataset (data/reference/refineries.csv).

Read-only: this script never modifies the source CSV.

Standard library only -- the project has no dependency manifest yet, so the
validator deliberately avoids pandas so it runs anywhere Python 3.8+ exists.

Exit codes:
    0  all critical checks passed (warnings may still be present)
    1  at least one CRITICAL check failed
    2  the dataset could not be read at all
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

# --- Expectations, as documented in the top-level README.md -----------------

EXPECTED_COLUMNS = [
    "refinery_id",
    "refinery_name",
    "company",
    "state",
    "capacity_mmtpa",
    "source",
    "source_url",
    "report_date",
    "retrieved_at",
]

REQUIRED_NON_BLANK = EXPECTED_COLUMNS  # every documented column is required
PROVENANCE_COLUMNS = ["source", "source_url", "report_date", "retrieved_at"]

EXPECTED_ROW_COUNT = 24
EXPECTED_TOTAL_CAPACITY = Decimal("267.116")
CAPACITY_TOLERANCE = Decimal("0.001")

ID_PATTERN = re.compile(r"^R\d{3}$")
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EXPECTED_SOURCE_URL = "https://ppac.gov.in/infrastructure/installed-refinery-capacity"

# States / union territories, used only to flag labels that are not
# conventional state names (a known PPAC quirk). Nothing is rewritten.
INDIAN_STATES_AND_UTS = {
    "ANDHRA PRADESH", "ARUNACHAL PRADESH", "ASSAM", "BIHAR", "CHHATTISGARH",
    "GOA", "GUJARAT", "HARYANA", "HIMACHAL PRADESH", "JHARKHAND", "KARNATAKA",
    "KERALA", "MADHYA PRADESH", "MAHARASHTRA", "MANIPUR", "MEGHALAYA",
    "MIZORAM", "NAGALAND", "ODISHA", "PUNJAB", "RAJASTHAN", "SIKKIM",
    "TAMIL NADU", "TELANGANA", "TRIPURA", "UTTAR PRADESH", "UTTARAKHAND",
    "WEST BENGAL", "ANDAMAN AND NICOBAR ISLANDS", "CHANDIGARH",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU", "DELHI", "JAMMU AND KASHMIR",
    "LADAKH", "LAKSHADWEEP", "PUDUCHERRY",
}


class Report:
    """Collects check results and tracks whether anything critical failed."""

    def __init__(self):
        self.critical_failures = []
        self.warnings = []

    def section(self, title):
        print()
        print(title)
        print("-" * len(title))

    def ok(self, msg):
        print("  [PASS]  " + msg)

    def fail(self, msg):
        print("  [FAIL]  " + msg)
        self.critical_failures.append(msg)

    def warn(self, msg):
        print("  [WARN]  " + msg)
        self.warnings.append(msg)

    def info(self, msg):
        print("  [INFO]  " + msg)


def load_rows(csv_path):
    """Return (header, rows, ragged_line_numbers). Never writes to the file."""
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError("CSV is empty -- no header row found")
        rows = []
        ragged = []
        for line_no, raw in enumerate(reader, start=2):
            if not raw:
                continue
            if len(raw) != len(header):
                ragged.append(line_no)
                continue
            row = dict(zip(header, raw))
            row["__line__"] = line_no
            rows.append(row)
    return header, rows, ragged


def check_schema(rep, header, ragged):
    rep.section("A. SCHEMA")
    healthy = True

    stripped = [h.strip() for h in header]
    if stripped != header:
        rep.fail("Header contains leading/trailing whitespace in column names")
        healthy = False

    missing = [c for c in EXPECTED_COLUMNS if c not in stripped]
    unexpected = [c for c in stripped if c not in EXPECTED_COLUMNS]

    if missing:
        rep.fail("Missing expected column(s): {}".format(missing))
        healthy = False
    else:
        rep.ok("All {} expected columns present".format(len(EXPECTED_COLUMNS)))

    if unexpected:
        rep.fail("Unexpected column(s) present: {}".format(unexpected))
        healthy = False
    else:
        rep.ok("No unexpected columns")

    if not missing and not unexpected:
        if stripped == EXPECTED_COLUMNS:
            rep.ok("Column order matches the documented schema")
        else:
            rep.warn("Column order differs from documented schema: {}".format(stripped))

    dupe_cols = [c for c, n in Counter(stripped).items() if n > 1]
    if dupe_cols:
        rep.fail("Duplicate column name(s): {}".format(dupe_cols))
        healthy = False
    else:
        rep.ok("Column names are unique")

    if ragged:
        rep.fail("Row(s) with a field count differing from the header: lines {}".format(ragged))
        healthy = False
    else:
        rep.ok("Every row has exactly one value per column")

    return healthy


def check_row_integrity(rep, rows):
    rep.section("B. ROW INTEGRITY")
    stats = {}

    count = len(rows)
    stats["row_count"] = count
    if count == EXPECTED_ROW_COUNT:
        rep.ok("Row count = {} (matches documented {})".format(count, EXPECTED_ROW_COUNT))
    else:
        rep.fail("Row count = {}, expected {}".format(count, EXPECTED_ROW_COUNT))

    dupe_ids = {v: n for v, n in Counter(r["refinery_id"] for r in rows).items() if n > 1}
    stats["duplicate_ids"] = dupe_ids
    if dupe_ids:
        rep.fail("Duplicate refinery_id value(s): {}".format(dupe_ids))
    else:
        rep.ok("No duplicate refinery_id values")

    dupe_names = {v: n for v, n in Counter(r["refinery_name"] for r in rows).items() if n > 1}
    stats["duplicate_names"] = dupe_names
    if dupe_names:
        rep.fail("Duplicate refinery_name value(s): {}".format(dupe_names))
    else:
        rep.ok("No duplicate refinery_name values")

    blanks = []
    for row in rows:
        for col in REQUIRED_NON_BLANK:
            value = row.get(col, "")
            if value is None or value.strip() == "":
                blanks.append("line {} column '{}'".format(row["__line__"], col))
    stats["blank_count"] = len(blanks)
    if blanks:
        rep.fail("{} blank/null value(s) in required fields: {}".format(len(blanks), blanks))
    else:
        rep.ok("No blank or null values in any required field")

    return stats


def check_numeric(rep, rows):
    rep.section("C. NUMERIC VALIDATION (capacity_mmtpa)")
    stats = {}

    total = Decimal("0")
    non_numeric = []
    negative = []
    zero_rows = []

    for row in rows:
        raw = (row.get("capacity_mmtpa") or "").strip()
        try:
            value = Decimal(raw)
        except (InvalidOperation, ValueError):
            non_numeric.append("line {} ({}): {!r}".format(
                row["__line__"], row["refinery_id"], raw))
            continue
        total += value
        if value < 0:
            negative.append("{} ({}): {}".format(
                row["refinery_id"], row["refinery_name"], value))
        elif value == 0:
            zero_rows.append((row["refinery_id"], row["refinery_name"]))

    stats["non_numeric"] = non_numeric
    stats["negative"] = negative
    stats["zero_rows"] = zero_rows
    stats["total"] = total

    if non_numeric:
        rep.fail("Non-numeric capacity_mmtpa value(s): {}".format(non_numeric))
    else:
        rep.ok("All capacity_mmtpa values parse as numeric")

    if negative:
        rep.fail("Negative capacity_mmtpa value(s): {}".format(negative))
    else:
        rep.ok("No negative capacity_mmtpa values")

    if zero_rows:
        # Zero capacity is legitimate (non-operating plant), reported separately.
        rep.info("{} zero-capacity record(s) -- retained, not deleted:".format(len(zero_rows)))
        for rid, name in zero_rows:
            rep.info("           {}  {}".format(rid, name))
    else:
        rep.info("No zero-capacity records")

    delta = abs(total - EXPECTED_TOTAL_CAPACITY)
    if delta <= CAPACITY_TOLERANCE:
        rep.ok("Total installed capacity = {} MMTPA (matches documented {}, delta {})".format(
            total, EXPECTED_TOTAL_CAPACITY, delta))
    else:
        rep.fail("Total installed capacity = {} MMTPA, expected {} "
                 "(delta {} > tolerance {})".format(
                     total, EXPECTED_TOTAL_CAPACITY, delta, CAPACITY_TOLERANCE))

    return stats


def check_provenance(rep, rows):
    rep.section("D. PROVENANCE")
    stats = {}

    missing = []
    for row in rows:
        for col in PROVENANCE_COLUMNS:
            if not (row.get(col) or "").strip():
                missing.append("line {} column '{}'".format(row["__line__"], col))
    stats["missing_provenance"] = missing
    if missing:
        rep.fail("{} row(s) missing provenance values: {}".format(len(missing), missing))
    else:
        rep.ok("All {} rows carry source, source_url, report_date, retrieved_at".format(len(rows)))

    urls = Counter(r["source_url"].strip() for r in rows)
    stats["source_urls"] = dict(urls)
    if len(urls) == 1:
        only_url = next(iter(urls))
        rep.ok("source_url identical across all rows: {}".format(only_url))
        if only_url != EXPECTED_SOURCE_URL:
            rep.warn("source_url differs from the URL documented in README.md ({})".format(
                EXPECTED_SOURCE_URL))
        if not only_url.startswith("https://"):
            rep.warn("source_url is not an https:// URL")
    else:
        rep.warn("source_url is not uniform across rows: {}".format(dict(urls)))

    sources = Counter(r["source"].strip() for r in rows)
    stats["sources"] = dict(sources)
    if len(sources) == 1:
        rep.ok("source description identical across all rows ({} rows)".format(len(rows)))
    else:
        rep.warn("Multiple distinct source descriptions: {}".format(list(sources)))

    bad_dates = []
    parsed = {"report_date": [], "retrieved_at": []}
    for row in rows:
        for col in ("report_date", "retrieved_at"):
            raw = (row.get(col) or "").strip()
            if not ISO_DATE_PATTERN.match(raw):
                bad_dates.append("line {} {}={!r}".format(row["__line__"], col, raw))
                continue
            try:
                parsed[col].append(date.fromisoformat(raw))
            except ValueError:
                bad_dates.append("line {} {}={!r} (not a real date)".format(
                    row["__line__"], col, raw))
    stats["bad_dates"] = bad_dates
    if bad_dates:
        rep.fail("Malformed date value(s): {}".format(bad_dates))
    else:
        rep.ok("report_date and retrieved_at are valid ISO-8601 (YYYY-MM-DD) dates")

    if parsed["report_date"] and parsed["retrieved_at"]:
        rep.info("report_date range:  {} .. {}".format(
            min(parsed["report_date"]), max(parsed["report_date"])))
        rep.info("retrieved_at range: {} .. {}".format(
            min(parsed["retrieved_at"]), max(parsed["retrieved_at"])))
        inverted = []
        for r in rows:
            rd = (r["report_date"] or "").strip()
            ra = (r["retrieved_at"] or "").strip()
            if ISO_DATE_PATTERN.match(rd) and ISO_DATE_PATTERN.match(ra):
                if date.fromisoformat(ra) < date.fromisoformat(rd):
                    inverted.append("line {}".format(r["__line__"]))
        if inverted:
            rep.warn("retrieved_at earlier than report_date on: {}".format(inverted))
        else:
            rep.ok("retrieved_at is on or after report_date for every row")

    return stats


def check_identifiers(rep, rows):
    rep.section("E. IDENTIFIER VALIDATION")
    stats = {}

    malformed = []
    for r in rows:
        if not ID_PATTERN.match((r["refinery_id"] or "").strip()):
            malformed.append("line {}: {!r}".format(r["__line__"], r["refinery_id"]))
    stats["malformed_ids"] = malformed
    if malformed:
        rep.fail("refinery_id value(s) not matching R### format: {}".format(malformed))
    else:
        rep.ok("All refinery_id values match the R### format")

    ids = [(r["refinery_id"] or "").strip() for r in rows]
    if len(set(ids)) == len(ids):
        rep.ok("All {} refinery_id values are unique".format(len(ids)))
    else:
        rep.fail("refinery_id values are not unique")

    if not malformed and ids:
        numbers = sorted(int(i[1:]) for i in ids)
        expected = list(range(1, len(numbers) + 1))
        stats["id_range"] = (ids[0], ids[-1])
        if numbers == expected:
            rep.ok("refinery_id values are sequential with no gaps (R{:03d}..R{:03d})".format(
                numbers[0], numbers[-1]))
        else:
            gaps = sorted(set(expected) - set(numbers))
            rep.warn("refinery_id values are not a gapless 1..N sequence; missing {} "
                     "-- IDs left unchanged".format(["R{:03d}".format(g) for g in gaps]))
        if ids != sorted(ids):
            rep.warn("Rows are not stored in ascending refinery_id order")
        else:
            rep.ok("Rows are stored in ascending refinery_id order")

    return stats


def check_text_quality(rep, rows, header):
    rep.section("F. TEXT QUALITY")
    stats = {}

    whitespace = []
    for row in rows:
        for col in header:
            value = row.get(col)
            if value is not None and value != value.strip():
                whitespace.append("line {} column '{}': {!r}".format(
                    row["__line__"], col, value))
    stats["whitespace"] = whitespace
    if whitespace:
        rep.warn("{} field(s) with leading/trailing whitespace: {}".format(
            len(whitespace), whitespace))
    else:
        rep.ok("No leading or trailing whitespace in any field")

    def normalise(text):
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    near = {}
    for row in rows:
        near.setdefault(normalise(row["refinery_name"]), []).append(row["refinery_id"])
    collisions = {k: v for k, v in near.items() if len(v) > 1}
    stats["near_duplicate_names"] = collisions
    if collisions:
        rep.warn("Refinery names that collide once normalised: {}".format(collisions))
    else:
        rep.ok("No suspicious near-duplicate refinery names")

    company_variants = {}
    for row in rows:
        company_variants.setdefault(normalise(row["company"]), set()).add(row["company"])
    inconsistent = {k: sorted(v) for k, v in company_variants.items() if len(v) > 1}
    stats["company_case_variants"] = inconsistent
    if inconsistent:
        rep.warn("Same company spelled with differing case/punctuation: {}".format(inconsistent))
    else:
        rep.ok("No company name appears under conflicting spellings")

    companies = sorted({r["company"] for r in rows})
    upper = [c for c in companies if c.isupper()]
    mixed = [c for c in companies if not c.isupper()]
    stats["company_count"] = len(companies)
    stats["mixed_case_companies"] = mixed
    if mixed and upper:
        rep.warn("Mixed capitalisation convention in 'company': {} upper-case vs {} "
                 "mixed-case -- left as published: {}".format(len(upper), len(mixed), mixed))
    else:
        rep.ok("Capitalisation convention in 'company' is consistent")

    footnoted = [(r["refinery_id"], r["refinery_name"]) for r in rows if "*" in r["refinery_name"]]
    stats["footnoted_names"] = footnoted
    if footnoted:
        rep.info("Name(s) carrying a source footnote marker '*' -- preserved verbatim: {}".format(
            footnoted))

    return stats


def check_source_caveats(rep, rows, numeric):
    rep.section("G. DOCUMENTED SOURCE CAVEATS")
    stats = {}

    non_conventional = sorted({
        r["state"].strip() for r in rows
        if r["state"].strip().upper() not in INDIAN_STATES_AND_UTS
    })
    stats["non_conventional_states"] = non_conventional
    if non_conventional:
        rep.warn("State label(s) that are not conventional Indian state/UT names: {} "
                 "-- expected PPAC quirk, left as published".format(non_conventional))
        for label in non_conventional:
            affected = [(r["refinery_id"], r["refinery_name"]) for r in rows
                        if r["state"].strip() == label]
            rep.info("           {}: {}".format(label, affected))
    else:
        rep.ok("Every state label is a conventional Indian state/UT name")

    cauvery = [r for r in rows if "cauvery" in r["refinery_name"].lower()]
    stats["cauvery_present"] = bool(cauvery)
    if not cauvery:
        rep.fail("The documented 'CPCL, Cauvery Basin' record is absent -- "
                 "zero-capacity records must be retained, not deleted")
    else:
        for row in cauvery:
            capacity = Decimal((row["capacity_mmtpa"] or "0").strip())
            if capacity == 0:
                rep.ok("{} {!r} present at {} MMTPA -- retained as a non-operating record".format(
                    row["refinery_id"], row["refinery_name"], capacity))
            else:
                rep.warn("{} {!r} now reports {} MMTPA, but README documents 0.0 "
                         "-- verify against source".format(
                             row["refinery_id"], row["refinery_name"], capacity))

    rep.info("capacity_mmtpa is INSTALLED capacity as published by PPAC. It is not "
             "actual throughput and must not be used as a proxy for it.")

    return stats


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = Path(__file__).resolve().parent.parent / "reference" / "refineries.csv"
    parser = argparse.ArgumentParser(
        description="Validate the refinery master dataset (read-only).")
    parser.add_argument("--csv", type=Path, default=default_csv,
                        help="path to the dataset (default: {})".format(default_csv))
    args = parser.parse_args()

    csv_path = args.csv
    print("=" * 72)
    print("EnergyShield-AI :: refinery master dataset validation")
    print("=" * 72)
    print("Dataset : {}".format(csv_path))

    if not csv_path.is_file():
        print("\n  [ERROR] Dataset not found: {}".format(csv_path))
        return 2

    try:
        header, rows, ragged = load_rows(csv_path)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("\n  [ERROR] Could not read dataset: {}".format(exc))
        return 2

    print("Rows    : {} data row(s) + 1 header".format(len(rows)))
    print("Mode    : read-only (the source CSV is never modified)")

    rep = Report()
    schema_ok = check_schema(rep, header, ragged)

    if not schema_ok and any(c not in header for c in EXPECTED_COLUMNS):
        rep.section("SUMMARY")
        print("  Schema is broken; per-field checks were skipped.")
        print("\n  RESULT: FAIL ({} critical)".format(len(rep.critical_failures)))
        return 1

    check_row_integrity(rep, rows)
    numeric = check_numeric(rep, rows)
    check_provenance(rep, rows)
    check_identifiers(rep, rows)
    check_text_quality(rep, rows, header)
    check_source_caveats(rep, rows, numeric)

    rep.section("SUMMARY")
    print("  Rows validated        : {}".format(len(rows)))
    print("  Total capacity        : {} MMTPA".format(numeric["total"]))
    print("  Zero-capacity records : {}".format(len(numeric["zero_rows"])))
    print("  Critical failures     : {}".format(len(rep.critical_failures)))
    print("  Warnings              : {}".format(len(rep.warnings)))

    if rep.warnings:
        print("\n  Warnings (non-blocking, reviewed as source behaviour):")
        for w in rep.warnings:
            print("    - {}".format(w))

    if rep.critical_failures:
        print("\n  Critical failures:")
        for f in rep.critical_failures:
            print("    - {}".format(f))
        print("\n  RESULT: FAIL")
        return 1

    print("\n  RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
