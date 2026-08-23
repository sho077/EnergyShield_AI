import streamlit as st

from components.ui import evidence_note, header
from scenario_engine import SCENARIOS, run_scenario


def render(data, graph):
    header()
    st.title("What if a critical corridor is disrupted?")
    st.caption("Simulation using currently implemented reference + network data")

    c1, c2 = st.columns([2, 1])
    with c1:
        scenario_name = st.selectbox("Scenario", list(SCENARIOS.keys()))
    with c2:
        st.selectbox("Duration", ["7 days", "15 days", "30 days"])

    evidence_note(
        "This is a demo scenario walkthrough over the reference + computed network layers, not a live forecast. "
        "No probability, risk score, or real-world operational recommendation is produced."
    )

    result = run_scenario(data, graph, scenario_name)

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("Step 1 — Identify")
    st.json(result["step1"], expanded=False)

    st.subheader("Step 2 — Trace")
    st.json(result["step2"], expanded=False)

    st.subheader("Step 3 — Exposure")
    if not result["step3"]["exposed_refineries"].empty:
        st.dataframe(result["step3"]["exposed_refineries"], use_container_width=True, hide_index=True)
        st.metric("Total exposed capacity (modelled)", f"{result['step3']['total_exposed_capacity_mmtpa']} MMTPA")
    else:
        st.info("No refinery exposure is directly computable from the sourced network for this scenario.")
    st.caption(result["step3"]["caveat"])

    st.subheader("Step 4 — Alternatives")
    if result["step4"]["alternative_routes"]:
        st.dataframe(result["step4"]["alternative_routes"], use_container_width=True, hide_index=True)
    else:
        st.info("No alternate-routing model exists yet for this scenario type.")
    st.caption(result["step4"]["limitation"])

    st.subheader("Step 5 — Next intelligence")
    st.markdown(f"> {result['step5']}")

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    with e1:
        st.markdown("**EXPOSURE**")
        st.caption("What part of the modeled network is affected?")
        st.write(result["step1"])
    with e2:
        st.markdown("**NETWORK IMPACT**")
        st.caption("What nodes/links become unavailable in the scenario?")
        st.write(result["step2"])
    with e3:
        st.markdown("**DATA GAPS**")
        st.caption("What prevents a stronger real-world conclusion?")
        st.write(result["step4"]["limitation"])
