import streamlit as st

import analytics
from analytics import node_label
from components.ui import badge, evidence_note, header


def render(data, graph):
    header()
    st.header("Network Resilience")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Network nodes", len(graph["nodes"]))
    c2.metric("Verified edges", len(graph["edges"]))
    c3.metric("Connected components", len(graph["components"]))
    c4.metric("Isolated nodes", len(graph["isolated"]))

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("Connected components")
    for i, comp in enumerate(graph["components"], start=1):
        labels = sorted(node_label(graph, n) for n in comp)
        with st.expander(f"Component {i} — {len(comp)} nodes"):
            for lbl in labels:
                st.write("• " + lbl)

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("Isolated nodes")
    evidence_note(
        "No source-backed connection currently represented in the model. This reflects a documentation gap "
        "or a genuinely non-operational facility — not a claim that no real-world connection exists."
    )
    iso_rows = []
    for nid in graph["isolated"]:
        n = graph["nodes"][nid]
        iso_rows.append({"ID": nid, "Name": n["name"], "Type": n["type"]})
    st.dataframe(iso_rows, use_container_width=True, hide_index=True)

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("Refinery connectivity — ranked by capacity")
    df = analytics.refinery_connectivity_table(data, graph)
    st.dataframe(
        df.drop(columns=["Connected To"]),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Show connection detail per refinery"):
        st.dataframe(df[["Refinery", "Connected To"]], use_container_width=True, hide_index=True)
