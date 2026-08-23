#!/usr/bin/env python3
"""Analyse connectivity of the reference network graph.

Datasets read (all from data/reference/, read-only):
    refineries.csv, ports.csv, strategic_reserves.csv, pipelines.csv,
    network_links.csv

This is a REPORTING tool, not a PASS/FAIL gate: an isolated node is frequently
the correct, honest state of a sourced network (see docs/data_sources.md's
evidence-gap list), so this script never fails on isolated nodes. It exists to
make the graph's actual shape -- who is connected to whom, and who is not --
reproducible from the CSVs rather than asserted by hand in a report.

Usage:
    python data/validation/validate_network_connectivity.py

Output is plain text: node/edge counts by type, connected components, and the
isolated-node list. docs/network_connectivity_report.md is a curated,
annotated write-up of this script's output, not a separate analysis -- run
this script again after any change to the graph and re-check that report
still agrees with it.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common as c  # noqa: E402

NODE_DATASETS = {
    "refinery": ("refineries.csv", "refinery_id", "refinery_name"),
    "port": ("ports.csv", "port_id", "port_name"),
    "reserve": ("strategic_reserves.csv", "reserve_id", "reserve_name"),
    "pipeline": ("pipelines.csv", "pipeline_id", "pipeline_name"),
}


def load_nodes():
    nodes = {}  # node_id -> (node_type, name)
    counts = {}
    for node_type, (filename, id_col, name_col) in NODE_DATASETS.items():
        _, rows, _ = c.load_rows(c.REFERENCE_DIR / filename)
        counts[node_type] = len(rows)
        for r in rows:
            node_id = (r.get(id_col) or "").strip()
            name = (r.get(name_col) or "").strip()
            nodes[node_id] = (node_type, name)
    return nodes, counts


def load_edges():
    _, rows, _ = c.load_rows(c.REFERENCE_DIR / "network_links.csv")
    edges = []
    for r in rows:
        edges.append((
            (r.get("from_node_id") or "").strip(),
            (r.get("to_node_id") or "").strip(),
            (r.get("link_type") or "").strip(),
            (r.get("link_id") or "").strip(),
        ))
    return edges


def connected_components(nodes, edges):
    adjacency = defaultdict(set)
    for a, b, _, _ in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)

    seen = set()
    components = []
    for node_id in nodes:
        if node_id in seen:
            continue
        stack = [node_id]
        component = set()
        while stack:
            cur = stack.pop()
            if cur in component:
                continue
            component.add(cur)
            for nxt in adjacency.get(cur, ()):
                if nxt not in component:
                    stack.append(nxt)
        seen |= component
        components.append(component)
    return components


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    nodes, node_counts = load_nodes()
    edges = load_edges()

    print("=" * 72)
    print("NETWORK CONNECTIVITY ANALYSIS")
    print("=" * 72)
    print("Total reference nodes: {}".format(len(nodes)))
    for node_type, n in sorted(node_counts.items()):
        print("  {:<10} {}".format(node_type, n))
    print("Total edges (network_links.csv): {}".format(len(edges)))

    link_type_counts = Counter(lt for _, _, lt, _ in edges)
    print("\nEdges by link_type:")
    for lt, n in sorted(link_type_counts.items()):
        print("  {:<26} {}".format(lt, n))

    edge_touch = defaultdict(int)
    for a, b, _, _ in edges:
        edge_touch[a] += 1
        edge_touch[b] += 1

    connected_ids = {a for a, b, _, _ in edges} | {b for a, b, _, _ in edges}
    isolated = sorted(nid for nid in nodes if nid not in connected_ids)

    components = connected_components(nodes, edges)
    non_trivial = sorted((c for c in components if len(c) > 1), key=len, reverse=True)

    print("\nConnected components with >1 node: {}".format(len(non_trivial)))
    for i, comp in enumerate(non_trivial, start=1):
        labelled = sorted("{} ({})".format(nid, nodes[nid][1]) for nid in comp)
        print("  Component {} -- {} node(s):".format(i, len(comp)))
        for label in labelled:
            print("    - {}".format(label))

    print("\nIsolated nodes (0 edges): {}".format(len(isolated)))
    by_type = defaultdict(list)
    for nid in isolated:
        node_type, name = nodes[nid]
        by_type[node_type].append("{} ({})".format(nid, name))
    for node_type in sorted(by_type):
        print("  {} isolated {}(s):".format(len(by_type[node_type]), node_type))
        for label in sorted(by_type[node_type]):
            print("    - {}".format(label))

    print("\nDegree by node (edge count touching each node):")
    for nid in sorted(nodes, key=lambda x: (-edge_touch.get(x, 0), x)):
        node_type, name = nodes[nid]
        print("  {:<10} {:<8} {:<3} degree={}".format(node_type, nid, "", edge_touch.get(nid, 0)))


if __name__ == "__main__":
    main()
