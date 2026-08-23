import streamlit as st

from components.ui import badge, header


def render(data, graph):
    header()
    st.header("AI Roadmap")

    st.subheader("CURRENT")
    st.markdown(f"{badge('Reference Layer','green')} {badge('Network Layer','green')} {badge('Scenario Prototype','amber')}", unsafe_allow_html=True)
    st.caption("Source-backed reference data, sourced network edges, and this demo scenario walkthrough — all implemented today.")

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("NEXT")
    agents = [
        {
            "name": "Geopolitical Intelligence Agent",
            "input": "News feeds, sanctions updates, government advisories",
            "does": "Monitors chokepoint and supplier-country risk events",
            "output": "Structured risk events tagged to chokepoints/suppliers in this reference graph",
        },
        {
            "name": "Maritime Intelligence Agent",
            "input": "AIS vessel tracking, port congestion feeds",
            "does": "Tracks tanker movement and port throughput",
            "output": "Live vessel positions and ETA estimates linked to ports.csv",
        },
        {
            "name": "Supply Risk Agent",
            "input": "Outputs of the above two agents + this network graph",
            "does": "Combines geopolitical and maritime signals with network topology",
            "output": "Ranked exposure alerts for refineries/ports",
        },
    ]
    for a in agents:
        with st.expander(a["name"]):
            st.write(f"**Input:** {a['input']}")
            st.write(f"**What it will do:** {a['does']}")
            st.write(f"**Expected output:** {a['output']}")

    st.markdown("<div class='es-divider'></div>", unsafe_allow_html=True)
    st.subheader("LATER")
    later = [
        {"name": "Procurement Optimizer", "input": "Live prices, contracts, supply risk alerts", "does": "Recommends crude sourcing mix", "output": "Procurement scenarios ranked by cost/risk"},
        {"name": "Reserve Optimizer", "input": "Live inventory, demand forecasts", "does": "Recommends strategic reserve draw/release", "output": "Draw-down schedules"},
        {"name": "Full Digital Twin", "input": "All live feeds + reference network", "does": "Simulates the entire supply chain in real time", "output": "Live what-if simulation"},
        {"name": "Adaptive Decision Engine", "input": "Digital twin state", "does": "Autonomously proposes mitigations", "output": "Actionable recommendations with human sign-off"},
    ]
    for a in later:
        with st.expander(a["name"]):
            st.write(f"**Input:** {a['input']}")
            st.write(f"**What it will do:** {a['does']}")
            st.write(f"**Expected output:** {a['output']}")

    st.caption("None of the NEXT or LATER items are implemented. They describe the intended product vision only.")
