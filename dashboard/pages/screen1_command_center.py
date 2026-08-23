import streamlit as st

import analytics
from components.map_view import build_map, unplottable_table
from components.ui import badge, evidence_note, header, kpi_card


def render(data, graph):
    header()
    k = analytics.kpis(data, graph)
    v = analytics.validation_status(data)

    cols = st.columns(4)
    kpi_specs = [
        ("Refineries", str(k["refineries"])),
        ("Installed Capacity", f"{k['installed_capacity_mmtpa']:.1f} MMTPA"),
        ("Reference Ports", str(k["ports"])),
        ("Strategic Reserve Facilities", str(k["reserve_facilities"])),
    ]
    for col, (label, val) in zip(cols, kpi_specs):
        with col:
            kpi_card(label, val)

    cols2 = st.columns(4)
    kpi_specs2 = [
        ("Pipelines", str(k["pipelines"])),
        ("Verified Network Edges", str(k["network_edges"])),
        ("Connected Components", str(k["connected_components"])),
        ("Isolated Nodes", str(k["isolated_nodes"])),
    ]
    for col, (label, val) in zip(cols2, kpi_specs2):
        with col:
            kpi_card(label, val)

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    status_kind = "green" if v["overall"] == "PASS" else "red"
    st.markdown(
        f"**VALIDATION STATUS** &nbsp; {badge(v['overall'], status_kind)}",
        unsafe_allow_html=True,
    )
    with st.expander("Validation checks (computed live from the reference CSVs)"):
        for c in v["checks"]:
            st.write(("✅ " if c["pass"] else "❌ ") + c["check"] + " — " + c["detail"])

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("What the system knows today")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"**Reference Layer**<br>{badge('Verified', 'green')}", unsafe_allow_html=True)
        st.caption(f"{k['total_nodes']} nodes across refineries, ports, pipelines, reserves")
    with c2:
        st.markdown(f"**Network Layer**<br>{badge('Verified / Partially Connected', 'amber')}", unsafe_allow_html=True)
        st.caption(f"{k['connected_nodes']} of {k['total_nodes']} nodes in a sourced component")
    with c3:
        st.markdown(f"**Dynamic Intelligence**<br>{badge('Not Yet Connected', 'gray')}", unsafe_allow_html=True)
        st.caption("Live AIS, prices, geopolitical feeds — planned")
    with c4:
        st.markdown(f"**AI Decision Engine**<br>{badge('Planned', 'gray')}", unsafe_allow_html=True)
        st.caption("Autonomous agents — not implemented")

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("India network map")
    filt_cols = st.columns(5)
    labels = ["Refineries", "Ports", "Pipelines", "Reserves", "Chokepoints"]
    show = {}
    for col, lbl in zip(filt_cols, labels):
        with col:
            show[lbl] = st.checkbox(lbl, value=True, key=f"map_filter_{lbl}")

    fig, unplottable = build_map(data, graph, show)
    st.plotly_chart(fig, use_container_width=True)
    evidence_note(
        "Refineries, pipelines and strategic reserves publish no latitude/longitude in this project's reference "
        "data, so they are not plotted as points here (see Infrastructure tables for their full records). "
        "Only sourced links between two geolocatable endpoints are drawn as lines; the rest are listed below."
    )
    tbl = unplottable_table(graph, unplottable)
    if not tbl.empty:
        with st.expander(f"Network links not drawn on the map ({len(tbl)}) — endpoints lack coordinates"):
            st.dataframe(tbl, use_container_width=True, hide_index=True)

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("Jamnagar connectivity")
    j1, j2 = st.columns(2)
    with j1:
        st.markdown(
            """<div class="es-hero">
            <b>R022 — RIL, Jamnagar</b><br>33.0 MMTPA<br>
            """ + badge("Sikka crude marine connection verified", "green") + """
            </div>""",
            unsafe_allow_html=True,
        )
    with j2:
        st.markdown(
            """<div class="es-hero">
            <b>R023 — RPL (SEZ), Jamnagar</b><br>35.2 MMTPA<br>
            """ + badge("Shared Sikka crude marine connection verified", "green") + """
            </div>""",
            unsafe_allow_html=True,
        )
    evidence_note(
        "Caveat: individual SPM-to-refinery allocation at the shared Sikka marine terminal remains unresolved — "
        "see docs/network_connectivity_report.md."
    )
