"""India network map — plots only nodes/edges with sourced coordinates.

Edges whose endpoints cannot both be geolocated are listed in a table instead
of drawn, per the project's no-fabricated-geometry rule.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

MARKERS = {
    "refinery": {"color": "#3fb6ff", "symbol": "circle", "size": 11},
    "port": {"color": "#35d38a", "symbol": "square", "size": 9},
    "pipeline": {"color": "#f2b84b", "symbol": "diamond", "size": 9},
    "reserve": {"color": "#c792ea", "symbol": "triangle-up", "size": 10},
    "chokepoint": {"color": "#ef5a6f", "symbol": "x", "size": 10},
}


def _coord(row):
    try:
        lat = float(row.get("latitude"))
        lon = float(row.get("longitude"))
        return lat, lon
    except (TypeError, ValueError):
        return None


def build_map(data, graph, show_types: dict[str, bool]):
    fig = go.Figure()
    coords: dict[str, tuple] = {}

    if show_types.get("Refineries") and not data["refineries"].empty:
        for _, r in data["refineries"].iterrows():
            pass  # refineries have no published coordinates in this dataset

    if show_types.get("Ports"):
        pts = []
        for _, r in data["ports"].iterrows():
            c = _coord(r)
            if c:
                coords[r["port_id"]] = c
                pts.append((c[1], c[0], r["port_name"]))
        if pts:
            fig.add_trace(
                go.Scattermap(
                    lon=[p[0] for p in pts],
                    lat=[p[1] for p in pts],
                    text=[p[2] for p in pts],
                    mode="markers",
                    marker=dict(size=MARKERS["port"]["size"], color=MARKERS["port"]["color"]),
                    name="Ports",
                    hovertemplate="%{text}<extra>Port</extra>",
                )
            )

    if show_types.get("Chokepoints"):
        pts = []
        for _, r in data["chokepoints"].iterrows():
            c = _coord(r)
            if c:
                coords[r["chokepoint_id"]] = c
                pts.append((c[1], c[0], r["name"]))
        if pts:
            fig.add_trace(
                go.Scattermap(
                    lon=[p[0] for p in pts],
                    lat=[p[1] for p in pts],
                    text=[p[2] for p in pts],
                    mode="markers",
                    marker=dict(size=MARKERS["chokepoint"]["size"], color=MARKERS["chokepoint"]["color"], symbol="x"),
                    name="Chokepoints",
                    hovertemplate="%{text}<extra>Chokepoint</extra>",
                )
            )

    # Edges: only draw when both endpoints have coordinates (currently: none do,
    # since refineries/pipelines/reserves publish no lat/lon in this dataset).
    unplottable_edges = []
    if show_types.get("Pipelines") or show_types.get("Reserves"):
        pass
    for e in graph["edges"]:
        a, b = e["from"], e["to"]
        if a in coords and b in coords:
            fig.add_trace(
                go.Scattermap(
                    lon=[coords[a][1], coords[b][1]],
                    lat=[coords[a][0], coords[b][0]],
                    mode="lines",
                    line=dict(width=1.5, color="rgba(63,182,255,0.5)"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        else:
            unplottable_edges.append(e)

    fig.update_layout(
        map=dict(style="carto-darkmatter", center=dict(lat=20.5, lon=75), zoom=3.6),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0a0e14",
        legend=dict(font=dict(color="#e8ecf2"), bgcolor="rgba(15,20,29,0.6)"),
        height=560,
    )
    return fig, unplottable_edges


def unplottable_table(graph, unplottable_edges) -> pd.DataFrame:
    from analytics import node_label

    rows = []
    for e in unplottable_edges:
        rows.append(
            {
                "Link": e["link_id"],
                "From": node_label(graph, e["from"]),
                "To": node_label(graph, e["to"]),
                "Type": e["link_type"],
                "Reason": "Endpoint(s) lack published coordinates in this dataset",
            }
        )
    return pd.DataFrame(rows)
