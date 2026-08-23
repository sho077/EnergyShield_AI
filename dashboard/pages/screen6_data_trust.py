import streamlit as st

from components.ui import header


def render(data, graph):
    header()
    st.header("Data Trust & Provenance")

    st.subheader("Source registry")
    src = data["source_registry"]
    rows = []
    for _, r in src.iterrows():
        rows.append(
            {
                "Dataset": r["dataset_name"],
                "Source": r["source_name"],
                "Authority": r["authority_level"],
                "Update frequency": r["update_frequency"],
                "Last checked": r["last_checked"],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True, height=350)

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("Data categories")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**SOURCE-BACKED**")
        st.caption("Refineries, ports, pipelines, reserves, chokepoints, suppliers, sanctions — every row cites a primary source.")
    with c2:
        st.markdown("**COMPUTED**")
        st.caption("Geodesic route distances in data/processed/ — derived from source-backed coordinates, kept separate from reference data.")
    with c3:
        st.markdown("**MODELLED**")
        st.caption("Trade corridors in routes.csv — analyst-defined plausible routings, not observed shipments.")
    with c4:
        st.markdown("**NOT YET AVAILABLE**")
        st.caption("Live AIS, live prices, geopolitical risk scoring, forecasting — no data exists for these yet.")

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("Why trust this?")
    st.markdown(
        """
- ✓ Every reference dataset has provenance
- ✓ Network edges require source evidence
- ✓ Validators run before acceptance
- ✓ Unknown ≠ No
- ✓ Computed data is separated from source facts
        """
    )
    st.caption(f"{len(src)} source records across the reference layer. Run `python data/validation/validate_phase1.py` for the full validator suite.")
