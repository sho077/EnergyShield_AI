# EnergyShield AI — Demo Video Script (3–5 minutes)

This script narrates the MVP dashboard (`streamlit run dashboard/app.py`) in
the recommended demo sequence. Every number spoken is read live from the
dashboard at record time — nothing here is a pre-baked figure to memorize,
because the dashboard computes it from `data/reference/` and
`data/processed/` on each run.

Throughout: clearly distinguish **what is already implemented** from **what
the current MVP demonstrates** from **what comes next**. Never describe a
future capability as already complete.

---

## 0:00–0:20 — Problem statement

> "India imports the vast majority of its crude oil. That supply chain runs
> through a small number of chokepoints, ports, pipelines and refineries —
> and today there's no single, source-verified picture of how that network
> actually connects. EnergyShield AI starts by building that picture
> honestly: only what's backed by a real, cited source."

## 0:20–0:50 — Command Center

Open Screen 1. Point at the DEMO MODE badge.

> "This is the Executive Command Center. Every KPI here — refineries,
> installed capacity, ports, pipelines, verified network edges, connected
> components, isolated nodes — is computed live from our reference CSVs, not
> hardcoded. Validation status: PASS, checked against the same rules our CLI
> validators enforce."

Point at the four-layer story panel (Reference / Network / Dynamic
Intelligence / AI Decision Engine).

> "We're building in layers. Reference and Network layers are verified today.
> Dynamic intelligence and the AI decision engine are explicitly not yet
> connected — you'll see that called out everywhere in this build."

## 0:50–1:30 — India network map

Scroll to the map, toggle the layer filters.

> "This map plots only nodes and links we can actually geolocate from
> official sources — ports and chokepoints. Refineries, pipelines and
> reserves don't publish coordinates in our current sources, so instead of
> guessing, we list every unplotted link in a table below the map, with the
> reason it isn't drawn. No line on this map is inferred."

## 1:30–2:00 — Jamnagar connectivity example

Scroll to the Jamnagar hero cards.

> "Here's a concrete example of Phase 3 work: RIL Jamnagar and RPL SEZ
> Jamnagar — India's two largest refineries — were both isolated nodes in our
> graph until we traced their crude marine connection to the shared Sikka
> terminal through Reliance's own environmental-compliance filings. Both are
> now verified-connected, with one honest caveat: which specific SPM unit
> feeds which refinery isn't resolved yet."

## 2:00–2:50 — Hormuz scenario

Switch to Screen 5, select "Hormuz Disruption."

> "This is a demo scenario, not a live forecast. We identify which modelled
> routes cross the Strait of Hormuz, trace which Indian port that route
> feeds, and show which refineries have a sourced network connection to that
> port — with total exposed capacity computed from our own refinery data.
> Then we show modelled alternative corridors that don't cross Hormuz, and
> state plainly what would be needed to turn this into a real operational
> tool: live geopolitical and maritime intelligence."

## 2:50–3:20 — Data Trust / validation

Switch to Screen 6.

> "Every dataset here traces to a named source — PPAC, the Ministry of Ports
> Shipping and Waterways, ISPRL, EIA, or the refinery operators' own filings.
> We separate source-backed facts from computed distances and modelled
> corridors, and 'unknown' is recorded honestly instead of guessed."

## 3:20–4:00 — Future AI architecture

Switch to Screen 7.

> "Here's the roadmap: geopolitical, maritime and supply-risk agents next;
> procurement optimization, reserve optimization and a full digital twin
> later. None of this is built yet — this screen exists so the judges can see
> the full vision without us pretending it's already running."

Close on Screen 1.

> "That's EnergyShield AI today: a verified reference network, an honest
> resilience view, and a scenario prototype built entirely on real, sourced
> data — with a clear, credible path to the intelligence layers on top."
