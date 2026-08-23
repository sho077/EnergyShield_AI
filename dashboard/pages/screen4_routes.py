import streamlit as st

from components.ui import header, not_connected


def render(data, graph):
    header()
    st.header("Routes & Chokepoints")

    st.subheader("Trade corridors (modelled)")
    cr = data["computed_routes"]
    routes = data["routes"]
    rows = []
    for _, r in routes.iterrows():
        variants = cr[cr["route_id"] == r["route_id"]]
        if variants.empty:
            coverage, dist = "no computed segment", "—"
        else:
            v = variants.iloc[0]
            coverage = v["distance_coverage"] or "none"
            dist = f"{float(v['distance_km']):.0f} km" if v["distance_km"] else "not computable"
        rows.append(
            {
                "Route ID": r["route_id"],
                "Route": r["route_name"],
                "Chokepoints": r["chokepoints_involved"] or "—",
                "Distance": dist,
                "Distance coverage": coverage,
                "Transit time": "Not modelled",
                "Methodology": "Geodesic (haversine) — last coordinate-resolvable leg only",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "Distances are straight-line geodesic computations between sourced coordinates, not maritime sailing "
        "distances. No route has full origin-to-destination coverage — see docs/phase2_report.md §5."
    )

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("Chokepoints")
    cp_rows = []
    for _, r in data["chokepoints"].iterrows():
        cp_rows.append(
            {
                "Name": r["name"],
                "Type": r["type"],
                "Baseline flow (mbd)": r["baseline_oil_flow_mbd"] or "not sourced",
                "Historical period": r["flow_period"] or "—",
                "Source": r["source"],
                "Staleness": "STALE — see notes" if str(r["report_date"]) < "2020" else "Recent",
            }
        )
    st.dataframe(cp_rows, use_container_width=True, hide_index=True)

    st.markdown("**Dynamic risk layer**")
    not_connected("NOT YET CONNECTED")
