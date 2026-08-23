import streamlit as st

from analytics import node_label
from components.ui import header


def render(data, graph):
    header()
    st.header("Infrastructure")
    tabs = st.tabs(["Refineries", "Ports", "Pipelines", "Strategic Reserves"])

    with tabs[0]:
        rows = []
        for _, r in data["refineries"].iterrows():
            degree = len(graph["adjacency"].get(r["refinery_id"], ()))
            rows.append(
                {
                    "Refinery": r["refinery_name"],
                    "Company": r["company"],
                    "State": r["state"],
                    "Capacity (MMTPA)": r["capacity_mmtpa_num"],
                    "Verified Connections": degree,
                    "Source": r["source"],
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with tabs[1]:
        rows = []
        for _, r in data["ports"].iterrows():
            rows.append(
                {
                    "Port": r["port_name"],
                    "State": r["state"],
                    "Crude handling": r["crude_handling"] or "unknown",
                    "Refinery connected": r["refinery_connected"] or "unknown",
                    "Pipeline connected": r["pipeline_connected"] or "unknown",
                    "Storage connected": r["storage_connected"] or "unknown",
                    "Class": r["port_class"],
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("Fields recorded 'unknown' mean no source statement was found — not a finding of 'no'.")

    with tabs[2]:
        rows = []
        for _, r in data["pipelines"].iterrows():
            pid = r["pipeline_id"]
            connected_refineries = [
                node_label(graph, n)
                for n in graph["adjacency"].get(pid, ())
                if graph["nodes"].get(n, {}).get("type") == "refinery"
            ]
            marine_edges = [
                n for n in graph["adjacency"].get(pid, ()) if graph["nodes"].get(n, {}).get("type") == "port"
            ]
            rows.append(
                {
                    "Pipeline": r["pipeline_name"],
                    "Operator": r["operator"],
                    "Origin": r["origin_name"],
                    "Destination": r["destination_name"],
                    "Length (km)": r["length_km"],
                    "Capacity (MMTPA)": r["capacity_mmtpa"] or "not published",
                    "Connected refineries": "; ".join(connected_refineries) or "none sourced",
                    "Marine intake status": "Sourced port link" if marine_edges else "Unresolved — see notes",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("PL001 and PL005 have partially resolved marine intakes — see docs/network_connectivity_report.md §5.")

    with tabs[3]:
        rows = []
        for _, r in data["reserves"].iterrows():
            rows.append(
                {
                    "Reserve": r["reserve_name"],
                    "Location": r["location"],
                    "Status": r["operational_status"],
                    "Storage capacity (MMT)": r["capacity_mmt_num"],
                    "Connected refinery": r["connected_refinery_or_refineries"] or "not sourced",
                    "Source": r["source"],
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("Storage capacity is design/rated capacity, not current inventory or fill level — no inventory figure exists in this dataset.")
