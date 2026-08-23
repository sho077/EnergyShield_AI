#!/usr/bin/env python3
"""Validate the network link layer.

Datasets: data/reference/network_links.csv and data/reference/pipelines.csv
Read-only: this script never modifies either source CSV.

Network edges are far easier to guess than entity attributes, so this
validator's job is to make guessing fail loudly:

* Both endpoints must resolve BY ID against a real reference dataset, and the
  stored endpoint name must match that record's canonical name exactly. An edge
  can therefore never be anchored to a place, only to a record.
* Every edge must carry evidence: `notes` must open with 'Evidence: ' and say
  what the source 'Establishes: '. An edge whose note does not do both is an
  assertion without a source and fails.
* Language that betrays a geographic or speculative inference ('proximity',
  'nearby', 'assumed', 'presumably', ...) is rejected outright.
* `link_type` must agree with the two endpoint types, so a mislabelled edge
  cannot silently reverse a direction.
* No self-links, and no duplicate (from, to, link_type) triples.

Exit codes: 0 PASS, 1 critical FAIL, 2 either dataset unreadable.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

DATASET = "network links (network_links.csv + pipelines.csv)"

LINK_COLUMNS = [
    "link_id", "from_node_type", "from_node_id", "from_node_name",
    "to_node_type", "to_node_id", "to_node_name", "link_type", "operator",
    "status", "source", "source_url", "report_date", "retrieved_at", "notes",
]

LINK_REQUIRED = LINK_COLUMNS  # every column on an edge is mandatory

PIPELINE_COLUMNS = [
    "pipeline_id", "pipeline_name", "operator", "product", "origin_name",
    "destination_name", "length_km", "capacity_mmtpa", "status",
    "commissioned_date", "source", "source_url", "report_date", "retrieved_at",
    "notes",
]

PIPELINE_REQUIRED = [
    "pipeline_id", "pipeline_name", "operator", "product", "origin_name",
    "destination_name", "length_km", "status", "source", "source_url",
    "report_date", "retrieved_at", "notes",
]

PIPELINE_NULLABLE = ["capacity_mmtpa", "commissioned_date"]

# node_type -> (reference file, id column, canonical name column, id pattern)
NODE_TYPES = {
    "refinery": ("refineries.csv", "refinery_id", "refinery_name", "R"),
    "port": ("ports.csv", "port_id", "port_name", "PORT"),
    "reserve": ("strategic_reserves.csv", "reserve_id", "reserve_name", "SPR"),
    "pipeline": ("pipelines.csv", "pipeline_id", "pipeline_name", "PL"),
}

# link_type -> (from_node_type, to_node_type). A link_type is only meaningful
# if it agrees with its endpoints, otherwise a reversed edge reads as correct.
LINK_TYPES = {
    "refinery_to_port": ("refinery", "port"),
    "port_to_refinery": ("port", "refinery"),
    "refinery_to_pipeline": ("refinery", "pipeline"),
    "pipeline_to_refinery": ("pipeline", "refinery"),
    "port_to_pipeline": ("port", "pipeline"),
    "pipeline_to_port": ("pipeline", "port"),
    "reserve_to_refinery": ("reserve", "refinery"),
    "reserve_to_port": ("reserve", "port"),
    "reserve_to_pipeline": ("reserve", "pipeline"),
    "port_to_reserve": ("port", "reserve"),
    "pipeline_to_reserve": ("pipeline", "reserve"),
}

STATUSES = {
    "operational", "under_construction", "approved_not_commissioned",
    "suspended", "decommissioned", "unknown",
}

PIPELINE_STATUSES = STATUSES

EVIDENCE_PREFIX = "Evidence: "
ESTABLISHES_MARKER = "Establishes: "
MIN_EVIDENCE_CHARS = 120

# Wording that means an endpoint was chosen from a map or a hunch rather than
# from a source. Note that plain 'near' is NOT banned: it occurs inside
# verbatim source quotes ('Salaya near Vadinar').
INFERENCE_MARKERS = [
    "proximity", "nearby", "adjacent to", "close to", "geographically",
    "assumed", "assuming", "presumably", "probably", "most likely",
    "appears to be", "we infer", "seems to",
]

# Self-links are structurally meaningless in this layer. If a real one is ever
# needed it must be listed here with a written justification, not just allowed.
JUSTIFIED_SELF_LINKS = {}


def load_reference(filename, id_column, name_column):
    """Return {id: canonical_name} for a sibling reference dataset."""
    path = c.REFERENCE_DIR / filename
    if not path.is_file():
        return None
    _, rows, _ = c.load_rows(path)
    return {(r.get(id_column) or "").strip(): (r.get(name_column) or "").strip()
            for r in rows}


def check_node_types(rep, rows):
    rep.section("L. NODE TYPES")
    bad = []
    for row in rows:
        for col in ("from_node_type", "to_node_type"):
            value = (row.get(col) or "").strip()
            if value not in NODE_TYPES:
                bad.append("{} {}={!r}".format(row.get("link_id"), col, value))
    if bad:
        rep.fail("node type(s) outside {}: {}".format(sorted(NODE_TYPES), bad))
    else:
        rep.ok("Every from_node_type and to_node_type is one of {}".format(
            sorted(NODE_TYPES)))
    return not bad


def check_link_types(rep, rows):
    rep.section("M. LINK TYPE AGREES WITH ITS ENDPOINTS")
    unknown, mismatched = [], []
    for row in rows:
        link_type = (row.get("link_type") or "").strip()
        pair = ((row.get("from_node_type") or "").strip(),
                (row.get("to_node_type") or "").strip())
        if link_type not in LINK_TYPES:
            unknown.append("{}: {!r}".format(row.get("link_id"), link_type))
            continue
        if LINK_TYPES[link_type] != pair:
            mismatched.append("{}: link_type {!r} implies {} but endpoints are "
                              "{}".format(row.get("link_id"), link_type,
                                          LINK_TYPES[link_type], pair))
    if unknown:
        rep.fail("link_type value(s) outside the controlled list {}: {}".format(
            sorted(LINK_TYPES), unknown))
    else:
        rep.ok("Every link_type is a permitted value")

    if mismatched:
        rep.fail("link_type disagreeing with its endpoint types -- a reversed or "
                 "mislabelled edge: {}".format(mismatched))
    else:
        rep.ok("Every link_type agrees with its from/to node types")

    counts = Counter((r.get("link_type") or "").strip() for r in rows)
    for name in sorted(counts):
        rep.info("{:<26} {} edge(s)".format(name, counts[name]))


def check_endpoints(rep, rows):
    """Endpoints must resolve BY ID, and the stored name must match exactly."""
    rep.section("N. ENDPOINT RESOLUTION (id AND canonical name)")
    caches = {}
    missing_dataset, bad_pattern, unresolved, name_mismatch = [], [], [], []

    for row in rows:
        for side in ("from", "to"):
            node_type = (row.get(side + "_node_type") or "").strip()
            node_id = (row.get(side + "_node_id") or "").strip()
            node_name = (row.get(side + "_node_name") or "").strip()
            where = "{} {}".format(row.get("link_id"), side)

            if node_type not in NODE_TYPES:
                continue  # already reported by check_node_types
            filename, id_column, name_column, prefix = NODE_TYPES[node_type]

            if not node_id.startswith(prefix):
                bad_pattern.append("{}: {!r} is not a {} id (expected {}...)".format(
                    where, node_id, node_type, prefix))
                continue

            if node_type not in caches:
                caches[node_type] = load_reference(filename, id_column, name_column)
            known = caches[node_type]
            if known is None:
                missing_dataset.append("{} ({})".format(filename, node_type))
                continue

            if node_id not in known:
                unresolved.append("{}: {!r} not found in {}".format(
                    where, node_id, filename))
                continue

            if known[node_id] != node_name:
                name_mismatch.append(
                    "{}: {} stores {!r} but {} says {!r}".format(
                        where, node_id, node_name, filename, known[node_id]))

    if missing_dataset:
        rep.fail("Reference dataset(s) not present, endpoints unverifiable: "
                 "{}".format(sorted(set(missing_dataset))))
    else:
        rep.ok("Every reference dataset needed to resolve endpoints is present")

    if bad_pattern:
        rep.fail("Endpoint id(s) not matching their node type's id prefix: {}".format(
            bad_pattern))
    else:
        rep.ok("Every endpoint id carries the id prefix of its node type")

    if unresolved:
        rep.fail("Endpoint(s) that do not exist in the referenced dataset: {}".format(
            unresolved))
    else:
        rep.ok("Every endpoint resolves by id against its reference dataset")

    if name_mismatch:
        rep.fail("Endpoint name(s) not matching the reference record exactly -- an "
                 "edge must be anchored to a record, never to a place name: "
                 "{}".format(name_mismatch))
    else:
        rep.ok("Every stored endpoint name matches its reference record exactly")

    per_type = Counter()
    for row in rows:
        per_type[(row.get("from_node_type") or "").strip()] += 1
        per_type[(row.get("to_node_type") or "").strip()] += 1
    for node_type in sorted(NODE_TYPES):
        rep.info("{:<10} referenced {} time(s) as an endpoint".format(
            node_type, per_type.get(node_type, 0)))


def check_self_and_duplicates(rep, rows):
    rep.section("O. SELF-LINKS AND DUPLICATE EDGES")

    self_links = []
    for row in rows:
        from_id = (row.get("from_node_id") or "").strip()
        to_id = (row.get("to_node_id") or "").strip()
        if from_id and from_id == to_id:
            link_id = (row.get("link_id") or "").strip()
            if link_id not in JUSTIFIED_SELF_LINKS:
                self_links.append("{}: {} -> {}".format(link_id, from_id, to_id))
    if self_links:
        rep.fail("Self-link(s) with no recorded justification: {}".format(self_links))
    else:
        rep.ok("No unjustified self-links")

    triples = Counter(((r.get("from_node_id") or "").strip(),
                       (r.get("to_node_id") or "").strip(),
                       (r.get("link_type") or "").strip()) for r in rows)
    dupes = {k: n for k, n in triples.items() if n > 1}
    rep.metric("duplicate_edges", len(dupes))
    if dupes:
        rep.fail("Duplicate (from, to, link_type) edge(s): {}".format(dupes))
    else:
        rep.ok("All {} edges are distinct on (from, to, link_type)".format(len(rows)))

    # A -> B and B -> A are both legal, but almost never both intended.
    directed = {((r.get("from_node_id") or "").strip(),
                 (r.get("to_node_id") or "").strip()) for r in rows}
    reciprocal = sorted({tuple(sorted(pair)) for pair in directed
                         if (pair[1], pair[0]) in directed})
    if reciprocal:
        rep.warn("Node pair(s) linked in both directions -- confirm each direction "
                 "is separately sourced: {}".format(reciprocal))
    else:
        rep.ok("No node pair is linked in both directions")


def check_evidence(rep, rows, label="P. EVIDENCE"):
    """No edge without a source statement. This is the rule that matters."""
    rep.section(label)

    no_prefix, thin, no_establishes = [], [], []
    for row in rows:
        row_id = (row.get("link_id") or row.get("pipeline_id") or "").strip()
        notes = (row.get("notes") or "").strip()
        if not notes.startswith(EVIDENCE_PREFIX):
            no_prefix.append(row_id)
            continue
        if len(notes) < MIN_EVIDENCE_CHARS:
            thin.append("{} ({} chars)".format(row_id, len(notes)))
        if ESTABLISHES_MARKER not in notes:
            no_establishes.append(row_id)

    if no_prefix:
        rep.fail("Row(s) whose notes do not open with {!r} -- an assertion with no "
                 "recorded source: {}".format(EVIDENCE_PREFIX, no_prefix))
    else:
        rep.ok("Every row opens its notes with {!r}".format(EVIDENCE_PREFIX))

    if thin:
        rep.fail("Row(s) whose evidence note is shorter than {} characters and "
                 "cannot be carrying a source statement: {}".format(
                     MIN_EVIDENCE_CHARS, thin))
    else:
        rep.ok("Every evidence note is at least {} characters".format(
            MIN_EVIDENCE_CHARS))

    if no_establishes:
        rep.fail("Row(s) not recording what the source {!r}: {}".format(
            ESTABLISHES_MARKER.strip(), no_establishes))
    else:
        rep.ok("Every row records what its source establishes")


def check_no_geographic_inference(rep, rows):
    rep.section("Q. NO GEOGRAPHIC OR SPECULATIVE INFERENCE")
    offenders = []
    for row in rows:
        row_id = (row.get("link_id") or row.get("pipeline_id") or "").strip()
        blob = " ".join((row.get(col) or "") for col in row
                        if col != "__line__").lower()
        for marker in INFERENCE_MARKERS:
            if marker in blob:
                offenders.append("{}: {!r}".format(row_id, marker))
    if offenders:
        rep.fail("Row(s) containing inference wording -- an endpoint may never be "
                 "chosen from a map or a hunch: {}".format(offenders))
    else:
        rep.ok("No row contains any of the {} banned inference markers".format(
            len(INFERENCE_MARKERS)))


def check_pipeline_usage(rep, link_rows, pipeline_rows):
    rep.section("R. PIPELINE MASTER <-> LINK COVERAGE")
    declared = {(r.get("pipeline_id") or "").strip() for r in pipeline_rows}
    used = set()
    for row in link_rows:
        for side in ("from", "to"):
            if (row.get(side + "_node_type") or "").strip() == "pipeline":
                used.add((row.get(side + "_node_id") or "").strip())

    dangling = sorted(used - declared)
    if dangling:
        rep.fail("Link(s) referencing a pipeline absent from pipelines.csv: "
                 "{}".format(dangling))
    else:
        rep.ok("Every pipeline endpoint is declared in pipelines.csv")

    unused = sorted(declared - used)
    if unused:
        rep.warn("Pipeline(s) in the master with no edge at all -- a node with no "
                 "edges adds nothing to the network: {}".format(unused))
    else:
        rep.ok("Every pipeline in the master carries at least one edge")

    # A pipeline that reaches a refinery but has no sourced marine intake is a
    # half-connected node. That is allowed, but it must be visible.
    inbound = {(r.get("to_node_id") or "").strip() for r in link_rows
               if (r.get("to_node_type") or "").strip() == "pipeline"}
    no_intake = sorted(declared - inbound)
    if no_intake:
        rep.info("{} pipeline(s) with no sourced upstream endpoint -- their marine "
                 "intake is an open evidence gap, see docs/data_sources.md: "
                 "{}".format(len(no_intake), no_intake))
    rep.metric("pipelines_with_sourced_intake",
               "{}/{}".format(len(declared & inbound), len(declared)))


def validate_pipelines(rep, header, rows, ragged):
    rep.section("A2. SCHEMA (pipelines.csv)")
    if [h.strip() for h in header] != PIPELINE_COLUMNS:
        rep.fail("pipelines.csv columns are {}, expected {}".format(
            header, PIPELINE_COLUMNS))
        return False
    rep.ok("pipelines.csv has exactly the {} expected columns".format(
        len(PIPELINE_COLUMNS)))
    if ragged:
        rep.fail("pipelines.csv ragged row(s) at lines {}".format(ragged))
        return False
    rep.ok("Every pipelines.csv row has one value per column")

    c.check_unique_id(rep, rows, "pipeline_id", r"^PL\d{3}$")
    c.check_required(rep, rows, PIPELINE_REQUIRED)
    c.check_nullable(rep, rows, PIPELINE_NULLABLE)
    c.check_numeric(rep, rows, "length_km", minimum=0)
    c.check_numeric(rep, rows, "capacity_mmtpa", minimum=0, allow_blank=True)
    c.check_provenance(rep, rows,
                       date_columns=("report_date", "retrieved_at",
                                     "commissioned_date"),
                       partial_ok=("commissioned_date",))
    c.check_controlled(rep, rows, {"status": PIPELINE_STATUSES},
                       section="H2. CONTROLLED VOCABULARY (pipelines.csv)")
    c.check_unique_text(rep, rows, "pipeline_name")
    c.check_whitespace(rep, rows, header)
    check_evidence(rep, rows, label="P2. EVIDENCE (pipelines.csv)")
    return True


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path,
                        default=c.REFERENCE_DIR / "network_links.csv")
    parser.add_argument("--pipelines-csv", type=Path,
                        default=c.REFERENCE_DIR / "pipelines.csv")
    args = parser.parse_args()

    for path in (args.csv, args.pipelines_csv):
        if not path.is_file():
            print("  [ERROR] Dataset not found: {}".format(path))
            return 2
    try:
        header, rows, ragged = c.load_rows(args.csv)
        pl_header, pl_rows, pl_ragged = c.load_rows(args.pipelines_csv)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print("  [ERROR] Could not read dataset: {}".format(exc))
        return 2

    c.banner(DATASET, "{} + {}".format(args.csv, args.pipelines_csv.name), len(rows))
    print("Pipelines: {} pipelines.csv row(s)".format(len(pl_rows)))
    rep = c.Report(DATASET)
    rep.metric("link_count", len(rows))
    rep.metric("pipeline_count", len(pl_rows))

    if not c.check_schema(rep, header, ragged, LINK_COLUMNS):
        rep.section("SUMMARY")
        print("  Schema is broken; per-field checks were skipped.")
        return 1

    if not validate_pipelines(rep, pl_header, pl_rows, pl_ragged):
        rep.section("SUMMARY")
        print("  pipelines.csv schema is broken; endpoint checks were skipped.")
        return 1

    c.check_unique_id(rep, rows, "link_id", r"^NL\d{3}$")
    c.check_required(rep, rows, LINK_REQUIRED)
    c.check_provenance(rep, rows, date_columns=("report_date", "retrieved_at"))
    c.check_controlled(rep, rows, {"status": STATUSES})
    c.check_whitespace(rep, rows, header)

    check_node_types(rep, rows)
    check_link_types(rep, rows)
    check_endpoints(rep, rows)
    check_self_and_duplicates(rep, rows)
    check_evidence(rep, rows)
    check_no_geographic_inference(rep, rows + pl_rows)
    check_pipeline_usage(rep, rows, pl_rows)

    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
