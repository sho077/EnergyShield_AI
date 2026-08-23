#!/usr/bin/env python3
"""Validate the Indian crude/petroleum port dataset.

Dataset: data/reference/ports.csv
Read-only: this script never modifies the source CSV.

Two checks here are doing real work beyond generic hygiene:

* Coordinates carry their OWN provenance (coordinate_source /
  coordinate_source_url), separate from the row's factual source, because the
  geolocation comes from OpenStreetMap while the crude-handling claim comes
  from a government publication. A populated coordinate with no coordinate
  provenance is a critical failure.
* The dataset must contain no fabricated capacity. Any column that looks like
  a throughput or capacity measure is rejected outright, since no per-port
  handling capacity was sourced in Phase 1.

Exit codes: 0 PASS, 1 critical FAIL, 2 dataset unreadable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "Indian crude/petroleum ports"

EXPECTED_COLUMNS = [
    "port_id", "port_name", "port_authority_or_operator", "parent_port_id",
    "city", "state", "country", "latitude", "longitude", "coordinate_precision",
    "coordinate_source", "coordinate_source_url", "port_class", "port_role",
    "crude_handling", "refinery_connected", "pipeline_connected",
    "storage_connected", "source", "source_url", "report_date", "retrieved_at",
    "notes",
]

REQUIRED_COLUMNS = [
    "port_id", "port_name", "port_authority_or_operator", "city", "state",
    "country", "port_class", "port_role", "crude_handling", "refinery_connected",
    "pipeline_connected", "storage_connected", "source", "source_url",
    "report_date", "retrieved_at", "notes",
]

NULLABLE_COLUMNS = [
    "parent_port_id", "latitude", "longitude", "coordinate_precision",
    "coordinate_source", "coordinate_source_url",
]

YES_NO_UNKNOWN = {"yes", "no", "unknown"}

PORT_CLASSES = {
    "major_port",
    "major_port_constituent_terminal",
    "major_port_constituent_dock",
    "major_port_notified_not_operational",
    "non_major_port",
}

COORDINATE_PRECISIONS = {"facility", "berth", "locality"}

# MoPNG-PS&W Ports Wing: "Presently, there are 14 Major Ports out of which 12
# Major Ports are operational."
EXPECTED_OPERATIONAL_MAJOR_PORTS = 12
EXPECTED_NOTIFIED_NOT_OPERATIONAL = 2

# India's land/maritime bounding box, generous enough to include the
# Andaman & Nicobar Islands.
INDIA_LAT = (6, 38)
INDIA_LON = (68, 98)


def check_coordinate_provenance(rep, rows):
    """A coordinate without its own source is an unattributed number."""
    rep.section("L. COORDINATE PROVENANCE")
    unattributed, orphaned, bad_precision = [], [], []

    for row in rows:
        has_coord = bool((row.get("latitude") or "").strip())
        has_src = bool((row.get("coordinate_source") or "").strip()
                       and (row.get("coordinate_source_url") or "").strip())
        precision = (row.get("coordinate_precision") or "").strip()

        if has_coord and not has_src:
            unattributed.append(row["port_id"])
        if has_src and not has_coord:
            orphaned.append(row["port_id"])
        if has_coord and precision not in COORDINATE_PRECISIONS:
            bad_precision.append("{}: {!r}".format(row["port_id"], precision))

    if unattributed:
        rep.fail("Coordinate(s) with no coordinate_source/coordinate_source_url: "
                 "{}".format(unattributed))
    else:
        rep.ok("Every populated coordinate carries its own separate provenance")

    if orphaned:
        rep.warn("Coordinate provenance recorded with no coordinate: {}".format(orphaned))

    if bad_precision:
        rep.fail("Coordinate(s) with a missing or invalid coordinate_precision "
                 "(expected one of {}): {}".format(sorted(COORDINATE_PRECISIONS),
                                                   bad_precision))
    else:
        rep.ok("Every populated coordinate declares its precision")

    locality = [r["port_id"] for r in rows
                if (r.get("coordinate_precision") or "").strip() == "locality"]
    if locality:
        rep.info("{} coordinate(s) are locality-level centroids, NOT berth positions: "
                 "{}".format(len(locality), locality))


def check_no_fabricated_capacity(rep, header, rows):
    rep.section("M. NO FABRICATED CAPACITY")
    suspect = [h for h in header
               if any(t in h.lower() for t in
                      ("capacity", "throughput", "tonnage", "mmtpa", "mtpa",
                       "traffic", "volume", "draft", "berths"))]
    if suspect:
        rep.fail("Column(s) implying an unsourced quantitative measure: {}. "
                 "No per-port handling capacity was sourced in Phase 1.".format(suspect))
    else:
        rep.ok("No handling-capacity or throughput column present")

    # Any row claiming crude_handling=yes must quote its evidence in notes.
    unevidenced = [r["port_id"] for r in rows
                   if (r.get("crude_handling") or "").strip() == "yes"
                   and "verbatim" not in (r.get("notes") or "").lower()]
    if unevidenced:
        rep.fail("Row(s) asserting crude_handling=yes without a verbatim source "
                 "quote in notes: {}".format(unevidenced))
    else:
        yes_rows = [r for r in rows if (r.get("crude_handling") or "").strip() == "yes"]
        rep.ok("All {} crude_handling=yes row(s) quote their source verbatim".format(
            len(yes_rows)))

    unknowns = [r["port_id"] for r in rows
                if (r.get("crude_handling") or "").strip() == "unknown"]
    rep.info("{} port(s) with crude_handling='unknown' -- no authoritative statement "
             "was located; this is NOT a finding of 'no': {}".format(
                 len(unknowns), unknowns))


def check_port_composition(rep, rows):
    """Cross-check the port_class split against the publisher's own count."""
    rep.section("N. MAJOR PORT COMPOSITION CROSS-CHECK")
    operational = [r for r in rows if (r.get("port_class") or "").strip() == "major_port"]
    notified = [r for r in rows
                if (r.get("port_class") or "").strip() == "major_port_notified_not_operational"]

    if len(operational) == EXPECTED_OPERATIONAL_MAJOR_PORTS:
        rep.ok("Operational Major Ports = {} (matches the MoPNG-PS&W Ports Wing "
               "statement)".format(len(operational)))
    else:
        rep.fail("Operational Major Ports = {}, MoPNG-PS&W states {}".format(
            len(operational), EXPECTED_OPERATIONAL_MAJOR_PORTS))

    if len(notified) == EXPECTED_NOTIFIED_NOT_OPERATIONAL:
        rep.ok("Notified-but-not-operational Major Ports = {} (14 notified minus 12 "
               "operational)".format(len(notified)))
    else:
        rep.fail("Notified-but-not-operational Major Ports = {}, expected {}".format(
            len(notified), EXPECTED_NOTIFIED_NOT_OPERATIONAL))

    unflagged = [r["port_id"] for r in notified
                 if "NOT OPERATIONAL" not in (r.get("notes") or "")]
    if unflagged:
        rep.fail("Notified-but-not-operational port(s) missing the 'NOT OPERATIONAL' "
                 "warning in notes: {}".format(unflagged))
    else:
        rep.ok("Every notified-but-not-operational port is flagged in notes")


def check_parent_references(rep, rows):
    """Constituent rows must point at a real parent and never be double-counted."""
    rep.section("O. PARENT / CONSTITUENT INTEGRITY")
    ids = {(r.get("port_id") or "").strip() for r in rows}
    constituent_classes = {"major_port_constituent_terminal",
                           "major_port_constituent_dock"}

    dangling, self_ref, missing_parent, unwarned = [], [], [], []
    for row in rows:
        pid = (row.get("port_id") or "").strip()
        parent = (row.get("parent_port_id") or "").strip()
        klass = (row.get("port_class") or "").strip()

        if parent:
            if parent not in ids:
                dangling.append("{} -> {}".format(pid, parent))
            if parent == pid:
                self_ref.append(pid)
        if klass in constituent_classes:
            if not parent:
                missing_parent.append(pid)
            if "never be summed" not in (row.get("notes") or ""):
                unwarned.append(pid)

    if dangling:
        rep.fail("parent_port_id value(s) pointing at no known port: {}".format(dangling))
    else:
        rep.ok("Every parent_port_id resolves to a port in this dataset")

    if self_ref:
        rep.fail("Row(s) naming themselves as parent: {}".format(self_ref))
    else:
        rep.ok("No self-referencing parent_port_id")

    if missing_parent:
        rep.fail("Constituent row(s) with no parent_port_id: {}".format(missing_parent))
    else:
        rep.ok("Every constituent terminal/dock names its parent port")

    if unwarned:
        rep.fail("Constituent row(s) missing the double-counting warning in notes: "
                 "{}".format(unwarned))
    else:
        rep.ok("Every constituent row warns against summing it with its parent")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    default_csv = c.REFERENCE_DIR / "ports.csv"
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

    c.check_unique_id(rep, rows, "port_id", r"^PORT\d{3}$")
    c.check_required(rep, rows, REQUIRED_COLUMNS)
    c.check_nullable(rep, rows, NULLABLE_COLUMNS)
    c.check_coordinates(rep, rows, allow_blank=True,
                        lat_range=INDIA_LAT, lon_range=INDIA_LON)
    c.check_provenance(rep, rows, date_columns=("report_date", "retrieved_at"))
    c.check_controlled(rep, rows, {
        "crude_handling": YES_NO_UNKNOWN,
        "refinery_connected": YES_NO_UNKNOWN,
        "pipeline_connected": YES_NO_UNKNOWN,
        "storage_connected": YES_NO_UNKNOWN,
        "port_class": PORT_CLASSES,
        "country": {"India"},
    })
    c.check_unique_text(rep, rows, "port_name")
    c.check_whitespace(rep, rows, header)

    check_coordinate_provenance(rep, rows)
    check_no_fabricated_capacity(rep, header, rows)
    check_port_composition(rep, rows)
    check_parent_references(rep, rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
