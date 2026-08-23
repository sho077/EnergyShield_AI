# EnergyShield AI — Presentation Outline

10 slides. Each includes a title, 3–5 key points, and the recommended
dashboard screenshot (see `docs/demo_assets.md` for the exact capture list).

---

### Slide 1 — Problem
- India imports the large majority of its crude oil.
- Supply routes concentrate through a handful of maritime chokepoints.
- No public, source-verified map of how India's refineries/ports/pipelines/
  reserves actually connect exists today.
- A disruption anywhere in that chain has no fast, credible way to be
  assessed.
- **Visual:** none (title slide).

### Slide 2 — Why existing systems are insufficient
- Commercial intelligence feeds (AIS, price terminals) show *symptoms*, not
  the underlying physical network.
- Public data (PPAC, port authority reports) is fragmented across dozens of
  documents with no unified, machine-readable graph.
- No existing public resource distinguishes verified fact from inferred
  connection.
- **Visual:** none.

### Slide 3 — EnergyShield AI concept
- A layered system: verified reference data → network graph → exposure
  analysis → scenario simulation → (future) live AI decision layer.
- Every layer is explicitly labelled by trust level: source-backed,
  computed, modelled, or not yet available.
- Built to be honest about gaps rather than to fill them with guesses.
- **Visual:** Screen 1, story panel (Reference/Network/Dynamic/AI layers).

### Slide 4 — Current implemented architecture
- `data/reference/` — 13 source-backed CSVs (refineries, ports, pipelines,
  reserves, chokepoints, suppliers, routes, sanctions, source registry).
- `data/processed/` — computed geodesic route distances, kept strictly
  separate from reference facts.
- A validation suite (10 validators) that must pass before any dataset
  change is accepted.
- A Streamlit MVP dashboard reading directly from these CSVs — no hardcoded
  demo numbers.
- **Visual:** Screen 1, top KPI row.

### Slide 5 — India reference network
- 24 refineries, 18 ports, 5 pipelines, 5 strategic reserve facilities.
- 23 sourced network edges connecting 32 of 52 total nodes.
- Every edge cites the exact operator/authority statement establishing it.
- Map shows only geolocatable nodes/links — no fabricated geometry.
- **Visual:** Screen 1, network map with filters shown.

### Slide 6 — Verified connectivity / Jamnagar example
- RIL Jamnagar (33.0 MMTPA) and RPL SEZ Jamnagar (35.2 MMTPA) — India's two
  largest refineries — were isolated nodes until Phase 3.
- Traced to a shared Sikka crude marine terminal via Reliance's own MoEFCC
  compliance filings, corroborated by Gujarat Maritime Board's jetty
  register.
- Caveat retained: individual SPM-to-refinery allocation is unresolved.
- **Visual:** Screen 1, Jamnagar hero cards.

### Slide 7 — Scenario simulation
- Demo scenario engine: Hormuz, Red Sea, major port, major refinery
  disruption.
- Five-step walkthrough: Identify → Trace → Exposure → Alternatives → Next
  Intelligence.
- Exposure figures are computed from the actual network graph, not invented.
- Explicitly labelled as a demo prototype, not a live forecast.
- **Visual:** Screen 5, Hormuz Disruption result.

### Slide 8 — Data trust and validation
- Every dataset traces to a named, dated, authoritative source.
- Four-way categorization: source-backed / computed / modelled / not yet
  available.
- 10/10 Phase 1 validators pass; network-link and connectivity validators
  pass independently.
- "Unknown" is recorded honestly rather than inferred.
- **Visual:** Screen 6, Data Trust page.

### Slide 9 — Future AI agents
- Next: Geopolitical Intelligence Agent, Maritime Intelligence Agent, Supply
  Risk Agent.
- Later: Procurement Optimizer, Reserve Optimizer, full Digital Twin,
  Adaptive Decision Engine.
- Each is scoped with explicit input/process/output — not built yet.
- **Visual:** Screen 7, AI Roadmap.

### Slide 10 — Final vision / impact
- A trustworthy, source-verified digital twin of India's energy supply
  chain, layered with real-time intelligence and decision support.
- Built on a foundation that never conflates fact, computation, and model —
  a discipline most dashboards skip.
- Positions India's energy planners to answer "what's at risk, and what are
  the alternatives" with evidence, not guesswork.
- **Visual:** Screen 1, full command center.
