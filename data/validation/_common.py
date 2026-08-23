#!/usr/bin/env python3
"""Shared, read-only validation helpers for EnergyShield-AI reference datasets.

Standard library only, matching the contract established by
``validate_refineries.py``: no third-party packages, never writes to a source
file, and a PASS/FAIL result expressed through the process exit code.

``validate_refineries.py`` deliberately does NOT import this module. It was
written and independently validated first, and is left byte-for-byte untouched.
Everything here is for the datasets added afterwards.

Exit-code contract shared by every validator:
    0  all critical checks passed (warnings may still be present)
    1  at least one CRITICAL check failed
    2  the dataset could not be read at all
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Partial ISO dates (YYYY or YYYY-MM) are accepted only where a column is
# explicitly declared as allowing reduced precision.
PARTIAL_DATE_PATTERN = re.compile(r"^\d{4}(-\d{2})?(-\d{2})?$")

PROVENANCE_COLUMNS = ["source", "source_url", "retrieved_at"]

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "reference"


class Report:
    """Collects check results and tracks whether anything critical failed."""

    def __init__(self, dataset_name):
        self.dataset_name = dataset_name
        self.critical_failures = []
        self.warnings = []
        self.metrics = {}

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

    def metric(self, key, value):
        self.metrics[key] = value

    def finish(self):
        """Print the machine-readable-ish summary and return an exit code."""
        self.section("SUMMARY")
        for key in sorted(self.metrics):
            print("  {:<28}: {}".format(key, self.metrics[key]))
        print("  {:<28}: {}".format("critical_failures", len(self.critical_failures)))
        print("  {:<28}: {}".format("warnings", len(self.warnings)))

        if self.warnings:
            print("\n  Warnings (non-blocking):")
            for w in self.warnings:
                print("    - {}".format(w))

        if self.critical_failures:
            print("\n  Critical failures:")
            for f in self.critical_failures:
                print("    - {}".format(f))
            print("\n  RESULT: FAIL  [{}]".format(self.dataset_name))
            return 1

        print("\n  RESULT: PASS  [{}]".format(self.dataset_name))
        return 0


def load_rows(csv_path):
    """Return (header, rows, ragged_line_numbers). Never writes to the file."""
    with Path(csv_path).open(newline="", encoding="utf-8") as fh:
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


def banner(dataset_name, csv_path, row_count):
    print("=" * 72)
    print("EnergyShield-AI :: {} validation".format(dataset_name))
    print("=" * 72)
    print("Dataset : {}".format(csv_path))
    print("Rows    : {} data row(s) + 1 header".format(row_count))
    print("Mode    : read-only (the source CSV is never modified)")


# --- Generic checks ---------------------------------------------------------

def check_schema(rep, header, ragged, expected_columns):
    rep.section("A. SCHEMA")
    stripped = [h.strip() for h in header]
    fatal = False

    if stripped != header:
        rep.fail("Header contains leading/trailing whitespace in column names")

    missing = [c for c in expected_columns if c not in stripped]
    unexpected = [c for c in stripped if c not in expected_columns]

    if missing:
        rep.fail("Missing expected column(s): {}".format(missing))
        fatal = True
    else:
        rep.ok("All {} expected columns present".format(len(expected_columns)))

    if unexpected:
        rep.fail("Unexpected column(s) present: {}".format(unexpected))
    else:
        rep.ok("No unexpected columns")

    if not missing and not unexpected and stripped != expected_columns:
        rep.warn("Column order differs from the documented schema: {}".format(stripped))

    dupes = [c for c, n in Counter(stripped).items() if n > 1]
    if dupes:
        rep.fail("Duplicate column name(s): {}".format(dupes))
        fatal = True
    else:
        rep.ok("Column names are unique")

    if ragged:
        rep.fail("Row(s) whose field count differs from the header: lines {}".format(ragged))
    else:
        rep.ok("Every row has exactly one value per column")

    return not fatal


def check_unique_id(rep, rows, id_column, pattern=None, expect_sequential=True):
    rep.section("B. IDENTIFIERS ({})".format(id_column))
    ids = [(r.get(id_column) or "").strip() for r in rows]

    blank = [r["__line__"] for r, i in zip(rows, ids) if not i]
    if blank:
        rep.fail("Blank {} on line(s) {}".format(id_column, blank))
    else:
        rep.ok("No blank {} values".format(id_column))

    dupes = {v: n for v, n in Counter(ids).items() if n > 1}
    rep.metric("duplicate_ids", len(dupes))
    if dupes:
        rep.fail("Duplicate {} value(s): {}".format(id_column, dupes))
    else:
        rep.ok("All {} {} values are unique".format(len(ids), id_column))

    if pattern is not None:
        rx = re.compile(pattern)
        bad = ["line {}: {!r}".format(r["__line__"], i)
               for r, i in zip(rows, ids) if not rx.match(i)]
        if bad:
            rep.fail("{} value(s) not matching {}: {}".format(id_column, pattern, bad))
        else:
            rep.ok("All {} values match {}".format(id_column, pattern))

        if expect_sequential and not bad and ids:
            numbers = sorted(int(re.sub(r"\D", "", i)) for i in ids)
            if numbers != list(range(1, len(numbers) + 1)):
                rep.warn("{} values are not a gapless 1..N sequence -- "
                         "IDs are never renumbered by this script".format(id_column))
            else:
                rep.ok("{} values are sequential with no gaps".format(id_column))

    return ids


def check_required(rep, rows, required_columns):
    rep.section("C. REQUIRED FIELDS")
    blanks = []
    for row in rows:
        for col in required_columns:
            if not (row.get(col) or "").strip():
                blanks.append("line {} column '{}'".format(row["__line__"], col))
    rep.metric("required_blanks", len(blanks))
    if blanks:
        rep.fail("{} blank value(s) in required fields: {}".format(len(blanks), blanks))
    else:
        rep.ok("No blank values in any of the {} required field(s)".format(
            len(required_columns)))
    return blanks


def check_nullable(rep, rows, nullable_columns):
    """Report, without failing, how complete each optional column is.

    Blank means NULL by convention across every reference dataset here. A null
    is a documented absence of an authoritative value, never a placeholder for
    a guess, so this is informational only.
    """
    if not nullable_columns:
        return {}
    rep.section("D. NULL / COVERAGE (optional columns)")
    coverage = {}
    for col in nullable_columns:
        filled = sum(1 for r in rows if (r.get(col) or "").strip())
        coverage[col] = filled
        rep.info("{:<36} {}/{} populated".format(col, filled, len(rows)))
    return coverage


def check_numeric(rep, rows, column, minimum=None, maximum=None,
                  allow_blank=False, expected_total=None, tolerance=Decimal("0.001"),
                  subset=None):
    """Validate a numeric column exactly, using Decimal (no float drift)."""
    label = column if subset is None else "{} [{}]".format(column, subset[0])
    rep.section("E. NUMERIC ({})".format(label))
    target = rows if subset is None else [r for r in rows if subset[1](r)]

    total = Decimal("0")
    bad, out_of_range, zeros, blanks = [], [], [], []

    for row in target:
        raw = (row.get(column) or "").strip()
        if raw == "":
            if allow_blank:
                blanks.append(row["__line__"])
            else:
                bad.append("line {}: blank".format(row["__line__"]))
            continue
        try:
            value = Decimal(raw)
        except (InvalidOperation, ValueError):
            bad.append("line {}: {!r}".format(row["__line__"], raw))
            continue
        total += value
        if minimum is not None and value < minimum:
            out_of_range.append("line {}: {} < {}".format(row["__line__"], value, minimum))
        if maximum is not None and value > maximum:
            out_of_range.append("line {}: {} > {}".format(row["__line__"], value, maximum))
        if value == 0:
            zeros.append(row["__line__"])

    if bad:
        rep.fail("Non-numeric/missing {} value(s): {}".format(column, bad))
    else:
        rep.ok("All present {} values parse as numeric".format(column))

    if out_of_range:
        rep.fail("{} value(s) outside the permitted range: {}".format(column, out_of_range))
    else:
        rep.ok("All {} values are within the permitted range".format(column))

    if blanks:
        rep.info("{} null {} value(s) (line(s) {}) -- absence of an authoritative "
                 "value, not zero".format(len(blanks), column, blanks))
    if zeros:
        rep.info("{} zero-valued {} record(s) on line(s) {} -- retained, "
                 "not deleted".format(len(zeros), column, zeros))

    if expected_total is not None:
        delta = abs(total - expected_total)
        if delta <= tolerance:
            rep.ok("Total {} = {} (matches authoritative {}, delta {})".format(
                label, total, expected_total, delta))
        else:
            rep.fail("Total {} = {}, expected {} (delta {} > tolerance {})".format(
                label, total, expected_total, delta, tolerance))

    return total


def check_coordinates(rep, rows, lat_col="latitude", lon_col="longitude",
                      allow_blank=True, lat_range=(-90, 90), lon_range=(-180, 180)):
    rep.section("F. COORDINATES")
    bad, missing, present = [], [], 0
    for row in rows:
        lat_raw = (row.get(lat_col) or "").strip()
        lon_raw = (row.get(lon_col) or "").strip()
        if lat_raw == "" and lon_raw == "":
            missing.append(row["__line__"])
            continue
        if (lat_raw == "") != (lon_raw == ""):
            bad.append("line {}: only one of {}/{} is populated".format(
                row["__line__"], lat_col, lon_col))
            continue
        try:
            lat, lon = Decimal(lat_raw), Decimal(lon_raw)
        except (InvalidOperation, ValueError):
            bad.append("line {}: non-numeric coordinate ({!r}, {!r})".format(
                row["__line__"], lat_raw, lon_raw))
            continue
        present += 1
        if not (Decimal(lat_range[0]) <= lat <= Decimal(lat_range[1])):
            bad.append("line {}: latitude {} outside {}".format(row["__line__"], lat, lat_range))
        if not (Decimal(lon_range[0]) <= lon <= Decimal(lon_range[1])):
            bad.append("line {}: longitude {} outside {}".format(row["__line__"], lon, lon_range))

    rep.metric("coordinate_violations", len(bad))
    if bad:
        rep.fail("Coordinate problem(s): {}".format(bad))
    else:
        rep.ok("All populated coordinates are numeric and within valid ranges")

    if missing:
        if allow_blank:
            rep.info("{} row(s) with null coordinates (line(s) {}) -- no authoritative "
                     "geolocation available; see the row's notes".format(len(missing), missing))
        else:
            rep.fail("{} row(s) missing coordinates: line(s) {}".format(len(missing), missing))
    rep.metric("coordinates_populated", "{}/{}".format(present, len(rows)))
    return bad


def check_provenance(rep, rows, date_columns=("retrieved_at",),
                     partial_ok=(), require_https=True,
                     provenance_columns=PROVENANCE_COLUMNS):
    rep.section("G. PROVENANCE")
    missing = []
    for row in rows:
        for col in provenance_columns:
            if not (row.get(col) or "").strip():
                missing.append("line {} column '{}'".format(row["__line__"], col))
    rep.metric("provenance_gaps", len(missing))
    if missing:
        rep.fail("{} row(s) missing provenance: {}".format(len(missing), missing))
    else:
        rep.ok("All {} rows carry {}".format(len(rows), ", ".join(provenance_columns)))

    if require_https:
        non_https = sorted({(r.get("source_url") or "").strip() for r in rows
                            if (r.get("source_url") or "").strip()
                            and not r["source_url"].strip().startswith("https://")})
        if non_https:
            rep.warn("source_url value(s) not using https://: {}".format(non_https))
        else:
            rep.ok("Every source_url uses https://")

    bad_dates = []
    for row in rows:
        for col in date_columns:
            raw = (row.get(col) or "").strip()
            if raw == "":
                continue  # nullability is governed by check_required
            pattern = PARTIAL_DATE_PATTERN if col in partial_ok else ISO_DATE_PATTERN
            if not pattern.match(raw):
                bad_dates.append("line {} {}={!r}".format(row["__line__"], col, raw))
                continue
            if len(raw) == 10:
                try:
                    date.fromisoformat(raw)
                except ValueError:
                    bad_dates.append("line {} {}={!r} (not a real date)".format(
                        row["__line__"], col, raw))
    if bad_dates:
        rep.fail("Malformed date value(s): {}".format(bad_dates))
    else:
        rep.ok("All populated dates are ISO-8601 (YYYY-MM-DD{})".format(
            ", partial YYYY / YYYY-MM allowed on {}".format(list(partial_ok))
            if partial_ok else ""))

    urls = sorted({(r.get("source_url") or "").strip() for r in rows})
    rep.metric("distinct_source_urls", len(urls))
    rep.info("Distinct source_url values: {}".format(len(urls)))
    return missing


def check_controlled(rep, rows, column_values, section="H. CONTROLLED VOCABULARY"):
    """column_values: {column: set_of_allowed_values}. Blank is always allowed."""
    rep.section(section)
    violations = []
    for col, allowed in column_values.items():
        seen = Counter((r.get(col) or "").strip() for r in rows)
        bad = {v: n for v, n in seen.items() if v and v not in allowed}
        if bad:
            violations.append("{}: {}".format(col, bad))
            rep.fail("{} has value(s) outside the controlled list {}: {}".format(
                col, sorted(allowed), bad))
        else:
            rep.ok("{} uses only permitted values ({})".format(
                col, {k: v for k, v in seen.items() if k}))
    return violations


def check_unique_text(rep, rows, column):
    """Canonical-name uniqueness, including after case/punctuation normalisation."""
    rep.section("I. CANONICAL NAME UNIQUENESS ({})".format(column))
    values = [(r.get(column) or "").strip() for r in rows]
    dupes = {v: n for v, n in Counter(values).items() if n > 1}
    if dupes:
        rep.fail("Duplicate {} value(s): {}".format(column, dupes))
    else:
        rep.ok("All {} {} values are distinct".format(len(values), column))

    def normalise(text):
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    near = {}
    for r in rows:
        near.setdefault(normalise(r.get(column) or ""), []).append(r["__line__"])
    collisions = {k: v for k, v in near.items() if len(v) > 1}
    if collisions:
        rep.warn("{} values colliding once normalised: {}".format(column, collisions))
    else:
        rep.ok("No near-duplicate {} values after normalisation".format(column))
    return dupes


def check_whitespace(rep, rows, header):
    rep.section("J. TEXT QUALITY")
    offenders = []
    for row in rows:
        for col in header:
            value = row.get(col)
            if value is not None and value != value.strip():
                offenders.append("line {} column '{}'".format(row["__line__"], col))
    if offenders:
        rep.warn("{} field(s) with leading/trailing whitespace: {}".format(
            len(offenders), offenders))
    else:
        rep.ok("No leading or trailing whitespace in any field")
    return offenders


def check_foreign_key(rep, rows, column, valid_values, source_label, allow_blank=True,
                      multi_sep=None):
    """Referential integrity against another reference dataset."""
    rep.section("K. REFERENTIAL INTEGRITY ({} -> {})".format(column, source_label))
    unknown = []
    for row in rows:
        raw = (row.get(column) or "").strip()
        if not raw:
            if not allow_blank:
                unknown.append("line {}: blank".format(row["__line__"]))
            continue
        parts = [p.strip() for p in raw.split(multi_sep)] if multi_sep else [raw]
        for part in parts:
            if part and part not in valid_values:
                unknown.append("line {}: {!r}".format(row["__line__"], part))
    if unknown:
        rep.fail("{} value(s) not found in {}: {}".format(column, source_label, unknown))
    else:
        rep.ok("Every populated {} resolves against {}".format(column, source_label))
    return unknown


def load_reference_ids(filename, id_column):
    """Read an ID column from a sibling reference dataset (read-only)."""
    path = REFERENCE_DIR / filename
    if not path.is_file():
        return None
    _, rows, _ = load_rows(path)
    return {(r.get(id_column) or "").strip() for r in rows}
