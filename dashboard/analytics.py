"""Network-graph analytics computed live from the reference CSVs.

Mirrors the method in data/validation/validate_network_connectivity.py (undirected
adjacency over refineries/ports/pipelines/reserves as nodes, network_links.csv as
edges) so the dashboard's numbers never drift from the validator's.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd


def build_graph(data: dict[str, pd.DataFrame]):
    nodes: dict[str, dict] = {}

    for _, r in data["refineries"].iterrows():
        nodes[r["refinery_id"]] = {"type": "refinery", "name": r["refinery_name"], "row": r}
    for _, r in data["ports"].iterrows():
        nodes[r["port_id"]] = {"type": "port", "name": r["port_name"], "row": r}
    for _, r in data["pipelines"].iterrows():
        nodes[r["pipeline_id"]] = {"type": "pipeline", "name": r["pipeline_name"], "row": r}
    for _, r in data["reserves"].iterrows():
        nodes[r["reserve_id"]] = {"type": "reserve", "name": r["reserve_name"], "row": r}

    edges = []
    for _, r in data["network_links"].iterrows():
        edges.append(
            {
                "from": r["from_node_id"],
                "to": r["to_node_id"],
                "link_type": r["link_type"],
                "link_id": r["link_id"],
                "notes": r.get("notes", ""),
                "source": r.get("source", ""),
            }
        )

    adjacency: dict[str, set] = defaultdict(set)
    for e in edges:
        adjacency[e["from"]].add(e["to"])
        adjacency[e["to"]].add(e["from"])

    seen = set()
    components = []
    for nid in nodes:
        if nid in seen:
            continue
        stack = [nid]
        comp = set()
        while stack:
            cur = stack.pop()
            if cur in comp:
                continue
            comp.add(cur)
            for nxt in adjacency.get(cur, ()):
                if nxt not in comp:
                    stack.append(nxt)
        seen |= comp
        components.append(comp)

    connected_ids = {e["from"] for e in edges} | {e["to"] for e in edges}
    isolated = sorted(nid for nid in nodes if nid not in connected_ids)
    multi_node_components = sorted([c for c in components if len(c) > 1], key=len, reverse=True)

    return {
        "nodes": nodes,
        "edges": edges,
        "adjacency": adjacency,
        "components": multi_node_components,
        "isolated": isolated,
        "connected_ids": connected_ids,
    }


def kpis(data: dict[str, pd.DataFrame], graph: dict) -> dict:
    ref = data["refineries"]
    ports = data["ports"]
    operational_ports = ports[ports["port_class"].isin(["major_port", "major_port_constituent_terminal", "major_port_constituent_dock", "non_major_port"])]
    reserves = data["reserves"]
    commissioned_reserves = reserves[reserves["operational_status"] == "commissioned"]

    return {
        "refineries": len(ref),
        "installed_capacity_mmtpa": round(ref["capacity_mmtpa_num"].sum(), 1),
        "ports": len(operational_ports),
        "reserve_facilities": len(commissioned_reserves),
        "reserve_capacity_mmt": round(commissioned_reserves["capacity_mmt_num"].sum(), 2),
        "pipelines": len(data["pipelines"]),
        "network_edges": len(graph["edges"]),
        "connected_components": len(graph["components"]),
        "isolated_nodes": len(graph["isolated"]),
        "total_nodes": len(graph["nodes"]),
        "connected_nodes": len(graph["connected_ids"]),
    }


def node_label(graph: dict, node_id: str) -> str:
    n = graph["nodes"].get(node_id)
    return f"{node_id} ({n['name']})" if n else node_id


def refinery_connectivity_table(data: dict[str, pd.DataFrame], graph: dict) -> pd.DataFrame:
    rows = []
    for _, r in data["refineries"].iterrows():
        rid = r["refinery_id"]
        degree = len(graph["adjacency"].get(rid, ()))
        connections = [node_label(graph, nid) for nid in graph["adjacency"].get(rid, ())]
        if degree > 0:
            model_status = "Connected"
        elif (r["capacity_mmtpa_num"] or 0) == 0:
            model_status = "Not operational"
        else:
            model_status = "No sourced edge"
        rows.append(
            {
                "Refinery": r["refinery_name"],
                "Company": r["company"],
                "Capacity (MMTPA)": r["capacity_mmtpa_num"],
                "Verified Connections": degree,
                "Connected To": "; ".join(connections) if connections else "—",
                "Model Status": model_status,
                "Evidence Status": "Source-backed" if degree > 0 else "Evidence / connectivity gap",
            }
        )
    df = pd.DataFrame(rows).sort_values("Capacity (MMTPA)", ascending=False).reset_index(drop=True)
    return df


def validation_status(data: dict[str, pd.DataFrame]) -> dict:
    """Reference-integrity checks equivalent in spirit to the CLI validators,
    run in-process so the dashboard can show live PASS/FAIL without shelling out."""
    checks = []

    ref_ids = set(data["refineries"]["refinery_id"])
    port_ids = set(data["ports"]["port_id"])
    pipe_ids = set(data["pipelines"]["pipeline_id"])
    reserve_ids = set(data["reserves"]["reserve_id"])
    all_ids = ref_ids | port_ids | pipe_ids | reserve_ids

    nl = data["network_links"]
    bad_from = nl[~nl["from_node_id"].isin(all_ids)]
    bad_to = nl[~nl["to_node_id"].isin(all_ids)]
    checks.append(
        {
            "check": "network_links.csv endpoints resolve to a known node",
            "pass": bad_from.empty and bad_to.empty,
            "detail": f"{len(nl)} edges checked, {len(bad_from) + len(bad_to)} unresolved endpoint(s)",
        }
    )

    dup_ref = data["refineries"]["refinery_id"].duplicated().sum()
    dup_port = data["ports"]["port_id"].duplicated().sum()
    checks.append(
        {
            "check": "primary keys unique (refineries, ports)",
            "pass": dup_ref == 0 and dup_port == 0,
            "detail": f"{dup_ref} duplicate refinery id(s), {dup_port} duplicate port id(s)",
        }
    )

    cap_missing = data["refineries"]["capacity_mmtpa_num"].isna().sum()
    checks.append(
        {
            "check": "refinery capacity field numeric",
            "pass": cap_missing == 0,
            "detail": f"{cap_missing} refinery row(s) with non-numeric capacity",
        }
    )

    src = data["source_registry"]
    checks.append(
        {
            "check": "source registry populated",
            "pass": len(src) > 0,
            "detail": f"{len(src)} source record(s)",
        }
    )

    all_pass = all(c["pass"] for c in checks)
    return {"overall": "PASS" if all_pass else "FAIL", "checks": checks}
