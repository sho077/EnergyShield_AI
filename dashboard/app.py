import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analytics
from data_loader import load_all
from pages import (
    screen1_command_center,
    screen2_resilience,
    screen3_infrastructure,
    screen4_routes,
    screen5_scenario,
    screen6_data_trust,
    screen7_roadmap,
)

st.set_page_config(
    page_title="EnergyShield AI — Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

css_path = Path(__file__).resolve().parent / "styles.css"
st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

PAGES = {
    "1. Executive Command Center": screen1_command_center,
    "2. Network Resilience": screen2_resilience,
    "3. Infrastructure": screen3_infrastructure,
    "4. Routes & Chokepoints": screen4_routes,
    "5. Demo Scenario Simulator": screen5_scenario,
    "6. Data Trust": screen6_data_trust,
    "7. AI Roadmap": screen7_roadmap,
}

DEMO_SEQUENCE = list(PAGES.keys())


def main():
    data = load_all()
    graph = analytics.build_graph(data)

    st.sidebar.markdown("### 🛡️ EnergyShield AI")
    st.sidebar.caption("MVP Demonstration / Decision-Support Prototype")

    if "demo_step" not in st.session_state:
        st.session_state.demo_step = 0

    mode = st.sidebar.radio("Navigation", ["Free navigation", "Demo Walkthrough"])

    if mode == "Demo Walkthrough":
        step = st.session_state.demo_step
        current = DEMO_SEQUENCE[step]
        st.sidebar.progress((step + 1) / len(DEMO_SEQUENCE))
        st.sidebar.write(f"Step {step + 1} of {len(DEMO_SEQUENCE)}: **{current}**")
        c1, c2 = st.sidebar.columns(2)
        if c1.button("◀ Prev", disabled=step == 0, use_container_width=True):
            st.session_state.demo_step = max(0, step - 1)
            st.rerun()
        if c2.button("Next ▶", disabled=step == len(DEMO_SEQUENCE) - 1, use_container_width=True):
            st.session_state.demo_step = min(len(DEMO_SEQUENCE) - 1, step + 1)
            st.rerun()
        selection = current
    else:
        selection = st.sidebar.radio("Screens", list(PAGES.keys()), label_visibility="collapsed")

    st.sidebar.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.sidebar.caption(
        "Data sources: PPAC, MoPNG-PS&W, ISPRL, EIA, refinery/port operator filings. "
        "See Data Trust for full provenance."
    )

    PAGES[selection].render(data, graph)


if __name__ == "__main__":
    main()
