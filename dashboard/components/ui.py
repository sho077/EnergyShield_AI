"""Small reusable UI helpers shared across pages."""
from __future__ import annotations

import streamlit as st


def badge(text: str, kind: str = "gray") -> str:
    return f'<span class="es-badge es-badge-{kind}">{text}</span>'


def kpi_card(label: str, value: str):
    st.markdown(
        f"""<div class="es-card">
            <div class="es-kpi-value">{value}</div>
            <div class="es-kpi-label">{label}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def header():
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
            <div>
                <div style="font-size:1.6rem; font-weight:800; letter-spacing:0.02em;">ENERGYSHIELD AI</div>
                <div style="color:#99a3b3; font-size:0.95rem;">India Energy Supply Chain Resilience Command Center</div>
            </div>
            <div>{badge('DEMO MODE', 'demo')} &nbsp; {badge('REFERENCE + COMPUTED DATA', 'gray')}</div>
        </div>
        <div class="es-divider"></div>
        """,
        unsafe_allow_html=True,
    )


def not_connected(label: str = "Not yet connected"):
    st.markdown(
        f'<div class="es-card" style="text-align:center; color:#99a3b3;">○ {label}</div>',
        unsafe_allow_html=True,
    )


def evidence_note(text: str):
    st.markdown(
        f'<div style="font-size:0.82rem; color:#99a3b3; border-left:2px solid #3fb6ff; padding:6px 10px; margin:6px 0; background:rgba(63,182,255,0.05);">{text}</div>',
        unsafe_allow_html=True,
    )
