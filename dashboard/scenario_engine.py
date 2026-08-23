"""Demo scenario simulator.

Every number here is derived directly from data/reference + data/processed at
run time — nothing is hand-typed into this file. This is a DEMONSTRATION of
how the currently implemented reference + network layers could feed a future
disruption model; it is explicitly NOT a live forecast, and never invents
a probability, risk score, or capacity figure the data doesn't support.
"""
from __future__ import annotations

import pandas as pd

from analytics import node_label

SCENARIOS = {
    "Hormuz Disruption": {"kind": "chokepoint", "id": "CP001"},
    "Red Sea Disruption": {"kind": "chokepoint", "id": "CP002"},
    "Major Port Disruption": {"kind": "port", "id": "PORT016"},
    "Major Refinery Disruption": {"kind": "refinery", "id": "R022"},
}


def _routes_via_chokepoint(data, cp_id):
    routes = data["routes"]
    return routes[routes["chokepoints_involved"].fillna("").str.contains(cp_id)]


def _routes_without_chokepoint(data, cp_id):
    routes = data["routes"]
    mask = ~routes["chokepoints_involved"].fillna("").str.contains(cp_id)
    return routes[mask]


def run_chokepoint_scenario(data, graph, cp_id: str) -> dict:
    cp_row = data["chokepoints"][data["chokepoints"]["chokepoint_id"] == cp_id].iloc[0]
    via = _routes_via_chokepoint(data, cp_id)
    alt = _routes_without_chokepoint(data, cp_id)

    affected_ports = sorted(set(via["destination_port_id"].dropna()) - {""})
    exposed_refineries = []
    for pid in affected_ports:
        for nbr in graph["adjacency"].get(pid, ()):
            n = graph["nodes"].get(nbr)
            if n and n["type"] == "refinery":
                cap = n["row"].get("capacity_mmtpa_num")
                exposed_refineries.append(
                    {
                        "Refinery": n["name"],
                        "Capacity (MMTPA)": cap,
                        "Reached via port": node_label(graph, pid),
                    }
                )
    exposed_df = pd.DataFrame(exposed_refineries).drop_duplicates()
    total_exposed_capacity = (
        round(exposed_df["Capacity (MMTPA)"].astype(float).sum(), 1) if not exposed_df.empty else 0.0
    )

    step1 = {
        "chokepoint": cp_row["name"],
        "role": cp_row["strategic_role"],
        "baseline_flow_mbd": cp_row["baseline_oil_flow_mbd"],
        "flow_period": cp_row["flow_period"],
        "routes_via": via[["route_id", "route_name", "destination_port"]].to_dict("records"),
    }
    step2 = {
        "affected_ports": [node_label(graph, p) for p in affected_ports],
        "downstream_edges": [
            f"{node_label(graph, p)} -> {node_label(graph, nbr)}"
            for p in affected_ports
            for nbr in graph["adjacency"].get(p, ())
        ],
    }
    step3 = {
        "exposed_refineries": exposed_df,
        "total_exposed_capacity_mmtpa": total_exposed_capacity,
        "caveat": "Exposure is limited to refinery connections directly represented in network_links.csv for the destination port(s) of routes crossing this chokepoint. It is not a volumetric flow model.",
    }
    step4 = {
        "alternative_routes": alt[["route_id", "route_name", "primary_corridor"]].to_dict("records"),
        "limitation": "These are MODELLED corridors (routes.csv), not observed shipments — see docs/data_sources.md. No source establishes actual cargo volumes or redirect feasibility.",
    }
    step5 = "Next required layer: Live geopolitical + maritime + procurement intelligence."

    return {"step1": step1, "step2": step2, "step3": step3, "step4": step4, "step5": step5}


def run_port_scenario(data, graph, port_id: str) -> dict:
    port = data["ports"][data["ports"]["port_id"] == port_id].iloc[0]
    neighbors = graph["adjacency"].get(port_id, set())
    exposed_refineries = []
    for nbr in neighbors:
        n = graph["nodes"].get(nbr)
        if n and n["type"] == "refinery":
            exposed_refineries.append(
                {"Refinery": n["name"], "Capacity (MMTPA)": n["row"].get("capacity_mmtpa_num")}
            )
    exposed_df = pd.DataFrame(exposed_refineries).drop_duplicates()
    total = round(exposed_df["Capacity (MMTPA)"].astype(float).sum(), 1) if not exposed_df.empty else 0.0

    step1 = {"port": port["port_name"], "operator": port["port_authority_or_operator"]}
    step2 = {
        "downstream_edges": [f"{node_label(graph, port_id)} -> {node_label(graph, n)}" for n in neighbors]
    }
    step3 = {
        "exposed_refineries": exposed_df,
        "total_exposed_capacity_mmtpa": total,
        "caveat": "Exposure reflects only edges sourced in network_links.csv for this port. Alternate marine intake arrangements are not modelled.",
    }
    step4 = {
        "alternative_routes": [],
        "limitation": "No alternate-port routing model exists yet in this project; this is a network-topology view of what is directly connected, not a rerouting plan.",
    }
    step5 = "Next required layer: Live geopolitical + maritime + procurement intelligence."
    return {"step1": step1, "step2": step2, "step3": step3, "step4": step4, "step5": step5}


def run_refinery_scenario(data, graph, refinery_id: str) -> dict:
    ref = data["refineries"][data["refineries"]["refinery_id"] == refinery_id].iloc[0]
    neighbors = graph["adjacency"].get(refinery_id, set())
    step1 = {"refinery": ref["refinery_name"], "capacity_mmtpa": ref["capacity_mmtpa_num"], "company": ref["company"]}
    step2 = {
        "upstream_edges": [f"{node_label(graph, n)} -> {node_label(graph, refinery_id)}" for n in neighbors]
    }
    step3 = {
        "exposed_refineries": pd.DataFrame(
            [{"Refinery": ref["refinery_name"], "Capacity (MMTPA)": ref["capacity_mmtpa_num"]}]
        ),
        "total_exposed_capacity_mmtpa": ref["capacity_mmtpa_num"],
        "caveat": "Capacity at risk is the refinery's installed capacity, not throughput, output, or a fuel-shortage forecast.",
    }
    step4 = {
        "alternative_routes": [],
        "limitation": "This project does not model refinery-to-refinery substitution, product logistics, or demand-side impact.",
    }
    step5 = "Next required layer: Live geopolitical + maritime + procurement intelligence."
    return {"step1": step1, "step2": step2, "step3": step3, "step4": step4, "step5": step5}


def run_scenario(data, graph, scenario_name: str) -> dict:
    spec = SCENARIOS[scenario_name]
    if spec["kind"] == "chokepoint":
        return run_chokepoint_scenario(data, graph, spec["id"])
    if spec["kind"] == "port":
        return run_port_scenario(data, graph, spec["id"])
    return run_refinery_scenario(data, graph, spec["id"])
