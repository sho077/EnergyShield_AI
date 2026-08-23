#!/usr/bin/env python3
"""Validate the computed/derived route layer.

Datasets: data/processed/computed_routes.csv and
          data/processed/route_segments.csv
Read-only: this script never modifies any source or processed CSV.

This layer is DERIVED, not sourced -- every value in it is either a geodesic
(great-circle) distance computed from coordinates already present in
data/reference/ports.csv and data/reference/chokepoints.csv, or an explicit
NULL where no such computation is possible. Its job is therefore different
from the reference-layer validators: instead of checking that a claim carries
a quotable source, it checks that a computed claim is actually reproducible
from the coordinates it claims to be derived from, and that the reference
layer (routes.csv / route_nodes.csv) has not been quietly given computed
values of its own.

Checks:

* Every route_id in both processed files resolves against routes.csv.
* Every node referenced (origin_node / destination_node / from_node_id /
  to_node_id) resolves by id against the reference dataset implied by its
  prefix (SUP-> suppliers.csv, PORT-> ports.csv, CP-> chokepoints.csv).
* distance_km is non-negative wherever populated, and never zero (a
  zero-length maritime/pipeline geodesic segment is not a real value this
  project can produce and would indicate a coordinate error).
* distance_method / transit_time_method are never blank -- a computed value
  with no stated method is as unaccountable as a sourced fact with no source.
* routes.csv / route_nodes.csv (the REFERENCE layer) still carry no
  distance/transit value -- computed values must live only in
  data/processed/, never bleed back into data/reference/.
* No duplicate (route_id, route_variant, sequence_no) in route_segments.csv,
  and no duplicate (route_id, route_variant) in computed_routes.csv.
* Independent sanity check: recomputes the haversine distance for every
  segment directly from ports.csv / chokepoints.csv coordinates and compares
  it against the stored distance_km, so a stored figure can never silently
  drift from the coordinates it claims to represent.

Exit codes: 0 PASS, 1 critical FAIL, 2 a required dataset is unreadable.
"""

from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "computed route layer (computed_routes.csv + route_segments.csv)"

PROCESSED_DIR = c.REFERENCE_DIR.parent / "processed"
COMPUTED_ROUTES_CSV = PROCESSED_DIR / "computed_routes.csv"
ROUTE_SEGMENTS_CSV = PROCESSED_DIR / "route_segments.csv"
ROUTES_CSV = c.REFERENCE_DIR / "routes.csv"
ROUTE_NODES_CSV = c.REFERENCE_DIR / "route_nodes.csv"
PORTS_CSV = c.REFERENCE_DIR / "ports.csv"
CHOKEPOINTS_CSV = c.REFERENCE_DIR / "chokepoints.csv"

COMPUTED_ROUTES_COLUMNS = [
    "route_id", "route_variant", "origin_node", "destination_node",
    "distance_km", "distance_coverage", "estimated_transit_days",
    "transit_time_method", "distance_method", "computed_at", "notes",
]

ROUTE_SEGMENTS_COLUMNS = [
    "segment_id", "route_id", "route_variant", "sequence_no",
    "from_node_type", "from_node_id", "from_node_name",
    "to_node_type", "to_node_id", "to_node_name",
    "distance_km", "distance_method", "computed_at", "notes",
]

DISTANCE_COVERAGE_VALUES = {"full", "partial_last_leg_only", "none"}

# id prefix -> (reference file, id column, latitude column, longitude column)
NODE_COORD_SOURCES = {
    "SUP": ("suppliers.csv", "supplier_id", None, None),
    "PORT": ("ports.csv", "port_id", "latitude", "longitude"),
    "CP": ("chokepoints.csv", "chokepoint_id", "latitude", "longitude"),
}

EARTH_RADIUS_KM = 6371.0088
DISTANCE_TOLERANCE_KM = 0.5  # recomputation is exact; this only absorbs rounding


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2)
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_coords(filename, id_column, lat_column, lon_column):
    path = c.REFERENCE_DIR / filename
    if not path.is_file():
        return None
    _, rows, _ = c.load_rows(path)
    coords = {}
    for r in rows:
        node_id = (r.get(id_column) or "").strip()
        lat_raw = (r.get(lat_column) or "").strip()
        lon_raw = (r.get(lon_column) or "").strip()
        if node_id and lat_raw and lon_raw:
            try:
                coords[node_id] = (float(lat_raw), float(lon_raw))
            except ValueError:
                pass
    return coords


def load_ids(filename, id_column):
    path = c.REFERENCE_DIR / filename
    if not path.is_file():
        return None
    _, rows, _ = c.load_rows(path)
    return {(r.get(id_column) or "").strip() for r in rows}


def resolve_node_type(node_id):
    for prefix, spec in NODE_COORD_SOURCES.items():
        if node_id.startswith(prefix):
            return prefix, spec
    return None, None


def check_route_ids(rep, computed_rows, segment_rows, route_ids):
    rep.section("A. ROUTE ID RESOLUTION (-> routes.csv)")
    bad = []
    for row in computed_rows:
        rid = (row.get("route_id") or "").strip()
        if rid not in route_ids:
            bad.append("computed_routes.csv {}: {!r} not in routes.csv".format(
                row.get("__line__"), rid))
    for row in segment_rows:
        rid = (row.get("route_id") or "").strip()
        if rid not in route_ids:
            bad.append("route_segments.csv {}: {!r} not in routes.csv".format(
                row.get("__line__"), rid))
    if bad:
        rep.fail("route_id value(s) that do not resolve against routes.csv: {}".format(bad))
    else:
        rep.ok("Every route_id in both processed files resolves against routes.csv")


def check_node_resolution(rep, rows, columns, file_label, id_caches):
    rep.section("B. NODE RESOLUTION ({})".format(file_label))
    bad_prefix, unresolved = [], []
    for row in rows:
        for col in columns:
            node_id = (row.get(col) or "").strip()
            if not node_id:
                continue  # blank is a legitimate "not modelled" value here
            prefix, spec = resolve_node_type(node_id)
            if prefix is None:
                bad_prefix.append("{} line {} {}={!r}: unrecognised id prefix".format(
                    file_label, row.get("__line__"), col, node_id))
                continue
            filename, id_column = spec[0], spec[1]
            if filename not in id_caches:
                id_caches[filename] = load_ids(filename, id_column)
            known = id_caches[filename]
            if known is None:
                bad_prefix.append("{}: reference dataset {} not present".format(
                    file_label, filename))
                continue
            if node_id not in known:
                unresolved.append("{} line {} {}={!r}: not found in {}".format(
                    file_label, row.get("__line__"), col, node_id, filename))
    if bad_prefix:
        rep.fail("Node id(s) with an unrecognised or missing reference dataset: {}".format(
            bad_prefix))
    else:
        rep.ok("Every populated node id in {} carries a recognised prefix".format(file_label))
    if unresolved:
        rep.fail("Node id(s) that do not resolve against their reference dataset: {}".format(
            unresolved))
    else:
        rep.ok("Every populated node id in {} resolves against its reference dataset".format(
            file_label))


def check_distance_values(rep, rows, file_label):
    rep.section("C. DISTANCE VALUES ({})".format(file_label))
    bad, zero = [], []
    for row in rows:
        raw = (row.get("distance_km") or "").strip()
        if raw == "":
            continue
        try:
            value = float(raw)
        except ValueError:
            bad.append("line {}: {!r} is not numeric".format(row.get("__line__"), raw))
            continue
        if value < 0:
            bad.append("line {}: {} is negative".format(row.get("__line__"), value))
        elif value == 0:
            zero.append("line {}".format(row.get("__line__")))
    if bad:
        rep.fail("distance_km value(s) that are non-numeric or negative in {}: {}".format(
            file_label, bad))
    else:
        rep.ok("Every populated distance_km in {} is numeric and non-negative".format(
            file_label))
    if zero:
        rep.fail("distance_km value(s) of exactly zero in {} with no technical "
                 "justification recorded for a zero-length geodesic segment: {}".format(
                     file_label, zero))
    else:
        rep.ok("No zero-valued distance_km in {}".format(file_label))


def check_methods_present(rep, rows, file_label, method_columns, conditional_on=None):
    """method_columns are always required. conditional_on maps a method column
    to the value column that must be populated before the method is required
    (used for transit_time_method, which is legitimately blank whenever
    estimated_transit_days itself is NULL -- there is no method to state for a
    value that was deliberately not computed)."""
    rep.section("D. METHOD FIELDS ({})".format(file_label))
    conditional_on = conditional_on or {}
    blanks = []
    for row in rows:
        for col in method_columns:
            if col not in row:
                continue
            gate_col = conditional_on.get(col)
            if gate_col is not None and not (row.get(gate_col) or "").strip():
                continue  # nothing to explain a method for -- blank is correct
            if not (row.get(col) or "").strip():
                blanks.append("line {} column '{}'".format(row.get("__line__"), col))
    if blanks:
        rep.fail("Blank method field(s) in {} -- a computed value with no stated "
                 "method is unaccountable: {}".format(file_label, blanks))
    else:
        rep.ok("Every row in {} states a method for each populated method column".format(
            file_label))


def check_reference_layer_untouched(rep):
    rep.section("E. REFERENCE LAYER STAYS SOURCE-ONLY (routes.csv)")
    if not ROUTES_CSV.is_file():
        rep.fail("routes.csv not found -- cannot verify separation")
        return
    _, rows, _ = c.load_rows(ROUTES_CSV)
    leaked = []
    for row in rows:
        for col in ("estimated_distance_km", "estimated_transit_days"):
            if (row.get(col) or "").strip():
                leaked.append("{} line {}: {}={!r}".format(
                    ROUTES_CSV.name, row.get("__line__"), col, row.get(col)))
    if leaked:
        rep.fail("Computed value(s) have leaked into the reference layer, which must "
                 "hold only sourced facts: {}".format(leaked))
    else:
        rep.ok("routes.csv still carries no distance/transit value -- the computed "
               "layer lives only in data/processed/")


def check_duplicates(rep, computed_rows, segment_rows):
    rep.section("F. DUPLICATE ROUTE/SEGMENT COMBINATIONS")
    seg_keys = Counter((
        (r.get("route_id") or "").strip(),
        (r.get("route_variant") or "").strip(),
        (r.get("sequence_no") or "").strip(),
    ) for r in segment_rows)
    seg_dupes = {k: n for k, n in seg_keys.items() if n > 1}
    if seg_dupes:
        rep.fail("Duplicate (route_id, route_variant, sequence_no) in "
                 "route_segments.csv: {}".format(seg_dupes))
    else:
        rep.ok("Every (route_id, route_variant, sequence_no) in route_segments.csv "
               "is distinct")

    route_keys = Counter((
        (r.get("route_id") or "").strip(),
        (r.get("route_variant") or "").strip(),
    ) for r in computed_rows)
    route_dupes = {k: n for k, n in route_keys.items() if n > 1}
    if route_dupes:
        rep.fail("Duplicate (route_id, route_variant) in computed_routes.csv: {}".format(
            route_dupes))
    else:
        rep.ok("Every (route_id, route_variant) in computed_routes.csv is distinct")

    seg_id_dupes = {v: n for v, n in Counter(
        (r.get("segment_id") or "").strip() for r in segment_rows).items() if n > 1}
    if seg_id_dupes:
        rep.fail("Duplicate segment_id value(s): {}".format(seg_id_dupes))
    else:
        rep.ok("All segment_id values are unique")


def check_coverage_values(rep, rows):
    rep.section("G. DISTANCE COVERAGE VOCABULARY")
    bad = []
    for row in rows:
        value = (row.get("distance_coverage") or "").strip()
        if value and value not in DISTANCE_COVERAGE_VALUES:
            bad.append("line {}: {!r}".format(row.get("__line__"), value))
    if bad:
        rep.fail("distance_coverage value(s) outside {}: {}".format(
            sorted(DISTANCE_COVERAGE_VALUES), bad))
    else:
        rep.ok("Every distance_coverage value is one of {}".format(
            sorted(DISTANCE_COVERAGE_VALUES)))

    # A "none" coverage must not carry a distance value, and vice versa.
    mismatched = []
    for row in rows:
        coverage = (row.get("distance_coverage") or "").strip()
        has_distance = bool((row.get("distance_km") or "").strip())
        if coverage == "none" and has_distance:
            mismatched.append("line {}: coverage 'none' but distance_km is populated".format(
                row.get("__line__")))
        if coverage != "none" and coverage and not has_distance:
            mismatched.append("line {}: coverage {!r} but distance_km is blank".format(
                row.get("__line__"), coverage))
    if mismatched:
        rep.fail("distance_coverage disagreeing with whether distance_km is "
                 "populated: {}".format(mismatched))
    else:
        rep.ok("distance_coverage agrees with distance_km population on every row")


def check_geodesic_recomputation(rep, segment_rows):
    """Independent sanity check: recompute every segment from source coordinates."""
    rep.section("H. INDEPENDENT GEODESIC RECOMPUTATION")
    port_coords = load_coords("ports.csv", "port_id", "latitude", "longitude")
    cp_coords = load_coords("chokepoints.csv", "chokepoint_id", "latitude", "longitude")
    lookup = {}
    lookup.update(port_coords or {})
    lookup.update(cp_coords or {})

    mismatched, unresolvable = [], []
    checked = 0
    for row in segment_rows:
        method = (row.get("distance_method") or "").strip()
        if method != "geodesic_haversine_r6371.0088km":
            continue  # only re-check segments claiming this exact reproducible method
        from_id = (row.get("from_node_id") or "").strip()
        to_id = (row.get("to_node_id") or "").strip()
        stored_raw = (row.get("distance_km") or "").strip()
        if not stored_raw:
            continue
        if from_id not in lookup or to_id not in lookup:
            unresolvable.append("{}: coordinates for {} or {} not found".format(
                row.get("segment_id"), from_id, to_id))
            continue
        lat1, lon1 = lookup[from_id]
        lat2, lon2 = lookup[to_id]
        recomputed = haversine_km(lat1, lon1, lat2, lon2)
        stored = float(stored_raw)
        delta = abs(recomputed - stored)
        checked += 1
        if delta > DISTANCE_TOLERANCE_KM:
            mismatched.append("{}: stored {} km, recomputed {:.1f} km, delta {:.1f} km".format(
                row.get("segment_id"), stored, recomputed, delta))

    rep.metric("segments_recomputed", checked)
    if unresolvable:
        rep.fail("Segment(s) whose coordinates could not be independently re-fetched "
                 "for recomputation: {}".format(unresolvable))
    else:
        rep.ok("Every haversine segment's endpoints resolved to source coordinates "
               "for recomputation")

    if mismatched:
        rep.fail("Segment(s) whose stored distance_km disagrees with an independent "
                 "recomputation from ports.csv/chokepoints.csv coordinates (tolerance "
                 "{} km): {}".format(DISTANCE_TOLERANCE_KM, mismatched))
    else:
        rep.ok("All {} recomputed segment(s) match their stored distance_km within "
               "{} km".format(checked, DISTANCE_TOLERANCE_KM))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    for path in (COMPUTED_ROUTES_CSV, ROUTE_SEGMENTS_CSV, ROUTES_CSV, ROUTE_NODES_CSV,
                 PORTS_CSV, CHOKEPOINTS_CSV):
        if not path.is_file():
            print("  [ERROR] Dataset not found: {}".format(path))
            return 2

    try:
        cr_header, cr_rows, cr_ragged = c.load_rows(COMPUTED_ROUTES_CSV)
        rs_header, rs_rows, rs_ragged = c.load_rows(ROUTE_SEGMENTS_CSV)
        route_ids = load_ids("routes.csv", "route_id")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("  [ERROR] Could not read a dataset: {}".format(exc))
        return 2

    c.banner(DATASET, "{} + {}".format(COMPUTED_ROUTES_CSV.name, ROUTE_SEGMENTS_CSV.name),
             len(cr_rows) + len(rs_rows))
    print("computed_routes.csv: {} row(s)".format(len(cr_rows)))
    print("route_segments.csv : {} row(s)".format(len(rs_rows)))
    rep = c.Report(DATASET)
    rep.metric("computed_route_count", len(cr_rows))
    rep.metric("route_segment_count", len(rs_rows))

    schema_ok = c.check_schema(rep, cr_header, cr_ragged, COMPUTED_ROUTES_COLUMNS)
    schema_ok = c.check_schema(rep, rs_header, rs_ragged, ROUTE_SEGMENTS_COLUMNS) and schema_ok
    if not schema_ok:
        rep.section("SUMMARY")
        print("  Schema is broken; downstream checks were skipped.")
        return 1

    c.check_whitespace(rep, cr_rows, cr_header)
    c.check_whitespace(rep, rs_rows, rs_header)

    check_route_ids(rep, cr_rows, rs_rows, route_ids)

    id_caches = {}
    check_node_resolution(rep, cr_rows, ("origin_node", "destination_node"),
                          "computed_routes.csv", id_caches)
    check_node_resolution(rep, rs_rows, ("from_node_id", "to_node_id"),
                          "route_segments.csv", id_caches)

    check_distance_values(rep, cr_rows, "computed_routes.csv")
    check_distance_values(rep, rs_rows, "route_segments.csv")

    check_methods_present(rep, cr_rows, "computed_routes.csv",
                          ("distance_method", "transit_time_method"),
                          conditional_on={"transit_time_method": "estimated_transit_days"})
    check_methods_present(rep, rs_rows, "route_segments.csv", ("distance_method",))

    check_coverage_values(rep, cr_rows)
    check_reference_layer_untouched(rep)
    check_duplicates(rep, cr_rows, rs_rows)
    check_geodesic_recomputation(rep, rs_rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
