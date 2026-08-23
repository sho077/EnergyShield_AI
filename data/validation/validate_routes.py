#!/usr/bin/env python3
"""Validate the trade corridor datasets.

Datasets: data/reference/routes.csv and data/reference/route_nodes.csv
Read-only: this script never modifies either source CSV.

Corridors are the one part of the Phase 1 reference layer that is MODELLED
rather than observed, so this validator's job is mostly to stop that modelling
from being mistaken for evidence:

* Every route must be labelled 'modelled' and say so in its notes.
* estimated_distance_km and estimated_transit_days must be NULL. Phase 1
  sourced no transit figures, and a plausible-looking number here would be
  indistinguishable from a real one downstream.
* Every node must resolve to a real row in suppliers.csv, ports.csv or
  chokepoints.csv, or be a plain geographic name with no reference table.
* Node sequences must start at an origin, end at a destination port, and be
  contiguous - except where two nodes deliberately share a sequence number as
  alternative branches of the same leg, which must be marked as a branch group.

Exit codes: 0 PASS, 1 critical FAIL, 2 either dataset unreadable.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "trade corridors (routes + route_nodes)"

ROUTE_COLUMNS = [
    "route_id", "route_name", "corridor_status", "origin_country",
    "origin_supplier_id", "origin_port", "destination_port",
    "destination_port_id", "primary_corridor", "estimated_distance_km",
    "estimated_transit_days", "chokepoints_involved", "corridor_evidence",
    "corridor_evidence_url", "source", "source_url", "report_date",
    "retrieved_at", "notes",
]

ROUTE_REQUIRED = [
    "route_id", "route_name", "corridor_status", "destination_port",
    "destination_port_id", "primary_corridor", "source", "source_url",
    "report_date", "retrieved_at", "notes",
]

ROUTE_NULLABLE = [
    "origin_country", "origin_supplier_id", "origin_port",
    "estimated_distance_km", "estimated_transit_days", "chokepoints_involved",
    "corridor_evidence", "corridor_evidence_url",
]

NODE_COLUMNS = [
    "route_id", "sequence_no", "node_type", "node_id_or_name",
    "node_reference_table", "branch_group", "source", "source_url", "retrieved_at",
]

NODE_TYPES = {
    "origin_country", "export_terminal", "chokepoint", "sea_area",
    "destination_port", "refinery",
}

REFERENCE_TABLES = {
    "suppliers.csv": ("suppliers.csv", "supplier_id"),
    "ports.csv": ("ports.csv", "port_id"),
    "chokepoints.csv": ("chokepoints.csv", "chokepoint_id"),
    "refineries.csv": ("refineries.csv", "refinery_id"),
}

# Columns that must be empty in Phase 1 because nothing was sourced to fill them.
MUST_BE_NULL = ["estimated_distance_km", "estimated_transit_days"]

# routes.csv is the only dataset permitted a repo-relative source_url, because
# a modelled corridor's "source" is this project's own documented method, which
# has no public URL.
MODELLED_SOURCE_URL = "docs/data_sources.md#modelled-corridors"


def check_modelled_labelling(rep, rows):
    rep.section("L. MODELLED-CORRIDOR LABELLING")

    bad_status = [r["route_id"] for r in rows
                  if (r.get("corridor_status") or "").strip() != "modelled"]
    if bad_status:
        rep.fail("Route(s) whose corridor_status is not 'modelled': {}".format(bad_status))
    else:
        rep.ok("Every route is explicitly labelled corridor_status='modelled'")

    unwarned = [r["route_id"] for r in rows
                if "MODELLED CORRIDOR" not in (r.get("notes") or "")]
    if unwarned:
        rep.fail("Route(s) whose notes do not carry the 'MODELLED CORRIDOR' "
                 "warning: {}".format(unwarned))
    else:
        rep.ok("Every route states in its notes that it is modelled, not observed")

    unsourced = [r["route_id"] for r in rows
                 if not (r.get("corridor_evidence") or "").strip()]
    if unsourced:
        rep.info("{} route(s) with NO corridor evidence at all -- weakest rows in the "
                 "dataset, resolve in Phase 2: {}".format(len(unsourced), unsourced))
    evidenced = len(rows) - len(unsourced)
    rep.metric("routes_with_evidence", "{}/{}".format(evidenced, len(rows)))


def check_no_invented_transit(rep, rows):
    rep.section("M. NO INVENTED DISTANCE OR TRANSIT TIME")
    populated = []
    for row in rows:
        for col in MUST_BE_NULL:
            if (row.get(col) or "").strip():
                populated.append("{} {}={!r}".format(row["route_id"], col, row[col]))
    if populated:
        rep.fail("Phase 1 sourced no transit figures, but value(s) are present: "
                 "{}. A plausible-looking estimate here is indistinguishable from a "
                 "sourced one downstream.".format(populated))
    else:
        rep.ok("estimated_distance_km and estimated_transit_days are null on every route")

    unexplained = [r["route_id"] for r in rows
                   if "to be modelled later" not in (r.get("notes") or "").lower()]
    if unexplained:
        rep.fail("Route(s) not recording why distance/transit are null: {}".format(
            unexplained))
    else:
        rep.ok("Every route records the null transit figures as 'to be modelled later'")


def check_route_references(rep, rows):
    rep.section("N. ROUTE-LEVEL REFERENTIAL INTEGRITY")
    for column, filename, id_column in (
        ("origin_supplier_id", "suppliers.csv", "supplier_id"),
        ("destination_port_id", "ports.csv", "port_id"),
    ):
        known = c.load_reference_ids(filename, id_column)
        if known is None:
            rep.warn("{} not present -- {} was not checked".format(filename, column))
            continue
        bad = [r["route_id"] for r in rows
               if (r.get(column) or "").strip()
               and r[column].strip() not in known]
        if bad:
            rep.fail("{} value(s) not found in {}: {}".format(column, filename, bad))
        else:
            rep.ok("Every populated {} resolves against {}".format(column, filename))

    known_cp = c.load_reference_ids("chokepoints.csv", "chokepoint_id")
    if known_cp is None:
        rep.warn("chokepoints.csv not present -- chokepoints_involved was not checked")
    else:
        bad = []
        for row in rows:
            raw = (row.get("chokepoints_involved") or "").strip()
            for part in [p.strip() for p in raw.split(";") if p.strip()]:
                if part not in known_cp:
                    bad.append("{}: {!r}".format(row["route_id"], part))
        if bad:
            rep.fail("chokepoints_involved value(s) not in chokepoints.csv: {}".format(bad))
        else:
            rep.ok("Every chokepoint referenced by a route exists in chokepoints.csv")

    # A destination port that cannot receive crude makes the corridor meaningless.
    ports_path = c.REFERENCE_DIR / "ports.csv"
    if ports_path.is_file():
        _, port_rows, _ = c.load_rows(ports_path)
        crude_ok = {r["port_id"] for r in port_rows
                    if (r.get("crude_handling") or "").strip() == "yes"}
        bad = [r["route_id"] for r in rows
               if (r.get("destination_port_id") or "").strip()
               and r["destination_port_id"].strip() not in crude_ok]
        if bad:
            rep.fail("Route(s) terminating at a port whose crude_handling is not "
                     "'yes': {}".format(bad))
        else:
            rep.ok("Every route terminates at a port with crude_handling='yes'")


def check_node_sequences(rep, route_ids, node_rows):
    rep.section("O. NODE SEQUENCE INTEGRITY")

    by_route = defaultdict(list)
    for row in node_rows:
        by_route[(row.get("route_id") or "").strip()].append(row)

    dangling = sorted(set(by_route) - set(route_ids))
    if dangling:
        rep.fail("route_nodes rows referencing unknown route_id(s): {}".format(dangling))
    else:
        rep.ok("Every route_nodes row belongs to a route in routes.csv")

    nodeless = sorted(set(route_ids) - set(by_route))
    if nodeless:
        rep.fail("Route(s) in routes.csv with no nodes at all: {}".format(nodeless))
    else:
        rep.ok("Every route has at least one node")

    bad_seq, bad_start, bad_end, unmarked_branch = [], [], [], []

    for rid in sorted(set(route_ids) & set(by_route)):
        nodes = by_route[rid]
        try:
            numbers = sorted(int((n.get("sequence_no") or "").strip()) for n in nodes)
        except ValueError:
            bad_seq.append("{}: non-integer sequence_no".format(rid))
            continue

        distinct = sorted(set(numbers))
        if distinct != list(range(1, len(distinct) + 1)):
            bad_seq.append("{}: sequence numbers {} are not a contiguous 1..N".format(
                rid, distinct))

        # Repeated sequence numbers are legal ONLY as marked alternative branches.
        for number in distinct:
            sharing = [n for n in nodes
                       if int((n.get("sequence_no") or "0").strip()) == number]
            if len(sharing) > 1:
                groups = {(n.get("branch_group") or "").strip() for n in sharing}
                if len(groups) != 1 or "" in groups:
                    unmarked_branch.append("{} seq {}".format(rid, number))

        ordered = sorted(nodes, key=lambda n: int((n.get("sequence_no") or "0").strip()))
        if (ordered[0].get("node_type") or "").strip() not in (
                "origin_country", "export_terminal", "sea_area"):
            bad_start.append("{}: starts with node_type {!r}".format(
                rid, ordered[0].get("node_type")))
        if (ordered[-1].get("node_type") or "").strip() != "destination_port":
            bad_end.append("{}: ends with node_type {!r}".format(
                rid, ordered[-1].get("node_type")))

    for label, problems, ok_msg in (
        ("Sequence numbering", bad_seq, "Every route's node sequence is a contiguous 1..N"),
        ("Route start", bad_start, "Every route starts at an origin or transit node"),
        ("Route end", bad_end, "Every route ends at a destination_port node"),
        ("Unmarked branch", unmarked_branch,
         "Shared sequence numbers are all marked as alternative branch groups"),
    ):
        if problems:
            rep.fail("{} problem(s): {}".format(label, problems))
        else:
            rep.ok(ok_msg)

    branches = {(n.get("route_id"), n.get("branch_group")) for n in node_rows
                if (n.get("branch_group") or "").strip()}
    if branches:
        rep.info("{} alternative-branch group(s) present -- these are OR legs, not "
                 "sequential legs: {}".format(len(branches), sorted(branches)))


def check_node_references(rep, node_rows):
    rep.section("P. NODE-LEVEL REFERENTIAL INTEGRITY")

    bad_type = ["{} seq {}: {!r}".format(n.get("route_id"), n.get("sequence_no"),
                                         n.get("node_type"))
                for n in node_rows
                if (n.get("node_type") or "").strip() not in NODE_TYPES]
    if bad_type:
        rep.fail("node_type value(s) outside {}: {}".format(sorted(NODE_TYPES), bad_type))
    else:
        rep.ok("Every node_type is a permitted value")

    caches = {}
    unresolved, bad_table, unreferenced = [], [], 0

    for node in node_rows:
        table = (node.get("node_reference_table") or "").strip()
        value = (node.get("node_id_or_name") or "").strip()
        where = "{} seq {}".format(node.get("route_id"), node.get("sequence_no"))

        if not table:
            unreferenced += 1
            continue
        if table not in REFERENCE_TABLES:
            bad_table.append("{}: {!r}".format(where, table))
            continue
        if table not in caches:
            filename, id_column = REFERENCE_TABLES[table]
            caches[table] = c.load_reference_ids(filename, id_column)
        known = caches[table]
        if known is None:
            continue
        if value not in known:
            unresolved.append("{}: {!r} not in {}".format(where, value, table))

    if bad_table:
        rep.fail("node_reference_table value(s) naming an unknown dataset: {}".format(
            bad_table))
    else:
        rep.ok("Every node_reference_table names a known reference dataset")

    if unresolved:
        rep.fail("Node(s) whose id does not exist in the referenced dataset: {}".format(
            unresolved))
    else:
        rep.ok("Every referenced node id resolves in its reference dataset")

    rep.info("{} node(s) are plain geographic names with no reference table (sea "
             "areas and foreign export terminals not modelled as entities)".format(
                 unreferenced))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=c.REFERENCE_DIR / "routes.csv")
    parser.add_argument("--nodes-csv", type=Path,
                        default=c.REFERENCE_DIR / "route_nodes.csv")
    args = parser.parse_args()

    for path in (args.csv, args.nodes_csv):
        if not path.is_file():
            print("  [ERROR] Dataset not found: {}".format(path))
            return 2
    try:
        header, rows, ragged = c.load_rows(args.csv)
        node_header, node_rows, node_ragged = c.load_rows(args.nodes_csv)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("  [ERROR] Could not read dataset: {}".format(exc))
        return 2

    c.banner(DATASET, "{} + {}".format(args.csv, args.nodes_csv.name), len(rows))
    print("Nodes   : {} route_nodes row(s)".format(len(node_rows)))
    rep = c.Report(DATASET)
    rep.metric("route_count", len(rows))
    rep.metric("route_node_count", len(node_rows))

    schema_ok = c.check_schema(rep, header, ragged, ROUTE_COLUMNS)
    rep.section("A2. SCHEMA (route_nodes.csv)")
    node_schema_ok = True
    if [h.strip() for h in node_header] != NODE_COLUMNS:
        rep.fail("route_nodes.csv columns are {}, expected {}".format(
            node_header, NODE_COLUMNS))
        node_schema_ok = False
    else:
        rep.ok("route_nodes.csv has exactly the {} expected columns".format(
            len(NODE_COLUMNS)))
    if node_ragged:
        rep.fail("route_nodes.csv ragged row(s) at lines {}".format(node_ragged))
    else:
        rep.ok("Every route_nodes row has one value per column")

    if not (schema_ok and node_schema_ok):
        rep.section("SUMMARY")
        print("  Schema is broken; per-field checks were skipped.")
        return 1

    c.check_unique_id(rep, rows, "route_id", r"^RT\d{3}$")
    c.check_required(rep, rows, ROUTE_REQUIRED)
    c.check_nullable(rep, rows, ROUTE_NULLABLE)
    c.check_provenance(rep, rows, date_columns=("report_date", "retrieved_at"),
                       require_https=False)
    c.check_unique_text(rep, rows, "route_name")
    c.check_whitespace(rep, rows, header)

    # The repo-relative source_url is deliberate here; confirm it is the agreed
    # one rather than an accidentally broken link.
    wrong_url = [r["route_id"] for r in rows
                 if (r.get("source_url") or "").strip() != MODELLED_SOURCE_URL]
    rep.section("K2. MODELLED SOURCE URL")
    if wrong_url:
        rep.fail("Route(s) whose source_url is not the agreed modelled-corridor "
                 "reference {!r}: {}".format(MODELLED_SOURCE_URL, wrong_url))
    else:
        rep.ok("Every route points at {!r} -- a repo-relative reference, used because "
               "a modelled corridor has no external source URL".format(MODELLED_SOURCE_URL))

    check_modelled_labelling(rep, rows)
    check_no_invented_transit(rep, rows)
    check_route_references(rep, rows)

    route_ids = [(r.get("route_id") or "").strip() for r in rows]
    check_node_sequences(rep, route_ids, node_rows)
    check_node_references(rep, node_rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
