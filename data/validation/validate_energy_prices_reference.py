#!/usr/bin/env python3
"""Validate the energy price reference dataset.

Dataset: data/reference/energy_prices_reference.csv
Read-only: this script never modifies the source CSV.

This file defines WHERE prices come from. It must never contain a price. A
cached price in a version-controlled reference file is stale the moment it is
written and indistinguishable from a live one downstream, so the central check
here rejects any column or value that looks like a price observation.

Exit codes: 0 PASS, 1 critical FAIL, 2 dataset unreadable.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "energy price reference"

EXPECTED_COLUMNS = [
    "price_series_id", "benchmark", "series_name_as_published", "commodity",
    "unit", "currency", "frequency", "provider", "provider_authority_level",
    "series_start", "contains_price_values", "source", "source_url",
    "report_date", "retrieved_at", "notes",
]

REQUIRED_COLUMNS = [
    "price_series_id", "benchmark", "commodity", "unit", "contains_price_values",
    "source", "source_url", "report_date", "retrieved_at", "notes",
]

NULLABLE_COLUMNS = [
    "series_name_as_published", "currency", "frequency", "provider",
    "provider_authority_level", "series_start",
]

AUTHORITY_LEVELS = {
    "official_india", "official_international", "authoritative_public",
    "commercial", "secondary",
}

# Any column that could hold an observation rather than a definition.
PRICE_VALUE_COLUMNS = (
    "price", "value", "last", "close", "open", "high", "low", "spot_price",
    "quote", "usd_per", "inr_per", "latest",
)

# A bare decimal in a definition column is almost certainly a leaked quote.
DECIMAL_LIKE = re.compile(r"^\s*\d+(\.\d+)?\s*$")
VALUE_BEARING_COLUMNS = ("benchmark", "commodity", "unit", "currency", "frequency")


def check_contains_no_prices(rep, header, rows):
    rep.section("L. NO PRICE VALUES STORED")

    forbidden = [h for h in header
                 if any(t in h.lower() for t in PRICE_VALUE_COLUMNS)
                 and h not in ("price_series_id", "contains_price_values")]
    if forbidden:
        rep.fail("Column(s) capable of holding a price observation: {}. This file "
                 "defines series; it must never cache a price.".format(forbidden))
    else:
        rep.ok("No column can hold a price observation")

    declared = [r["price_series_id"] for r in rows
                if (r.get("contains_price_values") or "").strip() != "no"]
    if declared:
        rep.fail("Row(s) not declaring contains_price_values='no': {}".format(declared))
    else:
        rep.ok("Every row declares contains_price_values='no'")

    leaked = []
    for row in rows:
        for col in VALUE_BEARING_COLUMNS:
            value = (row.get(col) or "").strip()
            if value and DECIMAL_LIKE.match(value):
                leaked.append("{} {}={!r}".format(row["price_series_id"], col, value))
    if leaked:
        rep.fail("Bare numeric value(s) in a definition column, which look like leaked "
                 "quotes: {}".format(leaked))
    else:
        rep.ok("No definition column holds a bare numeric value")


def check_series_identity(rep, rows):
    rep.section("M. SERIES IDENTITY AND UNITS")

    no_unit = [r["price_series_id"] for r in rows if not (r.get("unit") or "").strip()]
    if no_unit:
        rep.fail("Series with no unit: {}. An unlabelled unit is how price data "
                 "silently changes meaning.".format(no_unit))
    else:
        rep.ok("Every series states its unit explicitly")

    # A monetary series needs a currency; a ratio series must NOT claim one.
    missing_currency, spurious_currency = [], []
    for row in rows:
        unit = (row.get("unit") or "").strip().lower()
        currency = (row.get("currency") or "").strip()
        if unit == "ratio":
            if currency:
                spurious_currency.append(row["price_series_id"])
        elif not currency:
            missing_currency.append(row["price_series_id"])

    if missing_currency:
        rep.fail("Monetary series with no currency: {}".format(missing_currency))
    else:
        rep.ok("Every monetary series states its currency")
    if spurious_currency:
        rep.fail("Non-monetary (ratio) series carrying a currency: {}".format(
            spurious_currency))
    else:
        rep.ok("No ratio series claims a currency")

    multi = [r["price_series_id"] for r in rows if ";" in (r.get("currency") or "")]
    if multi:
        rep.info("{} series published in more than one currency -- downstream code must "
                 "not mix them in one column: {}".format(len(multi), multi))

    no_provider = [r["price_series_id"] for r in rows
                   if not (r.get("provider") or "").strip()]
    if no_provider:
        rep.info("{} series with NO provider -- no official machine-readable source was "
                 "located; see the row's notes: {}".format(len(no_provider), no_provider))


def check_authority_levels(rep, rows):
    rep.section("N. PROVIDER AUTHORITY LEVEL")
    bad = ["{}: {!r}".format(r["price_series_id"], r.get("provider_authority_level"))
           for r in rows
           if (r.get("provider_authority_level") or "").strip()
           and r["provider_authority_level"].strip() not in AUTHORITY_LEVELS]
    if bad:
        rep.fail("provider_authority_level value(s) outside {}: {}".format(
            sorted(AUTHORITY_LEVELS), bad))
    else:
        rep.ok("Every populated provider_authority_level is a registry-valid level")

    india = [r["price_series_id"] for r in rows
             if (r.get("provider_authority_level") or "").strip() == "official_india"]
    if india:
        rep.ok("{} India-official series present ({}) -- the correct reference for "
               "India-specific price work".format(len(india), india))
    else:
        rep.warn("No official_india price series is recorded")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = c.REFERENCE_DIR / "energy_prices_reference.csv"
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

    c.check_unique_id(rep, rows, "price_series_id", r"^PRC\d{3}$")
    c.check_required(rep, rows, REQUIRED_COLUMNS)
    c.check_nullable(rep, rows, NULLABLE_COLUMNS)
    c.check_provenance(rep, rows, date_columns=("report_date", "retrieved_at",
                                                "series_start"),
                       partial_ok=("series_start",))
    c.check_controlled(rep, rows, {"contains_price_values": {"no"}})
    c.check_unique_text(rep, rows, "benchmark")
    c.check_whitespace(rep, rows, header)

    check_contains_no_prices(rep, header, rows)
    check_series_identity(rep, rows)
    check_authority_levels(rep, rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
