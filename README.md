# EnergyShield-AI

AI-Driven Energy Supply Chain Resilience Platform for India.

The goal is a decision-support system that models India's downstream petroleum
supply chain — refineries, transport links, and demand centres — and answers
resilience questions against it: if a node or corridor goes down, what capacity
is at risk, which regions are exposed, and how should flows be re-routed?

## Status

**Phase 1 — Data Foundation: complete and validated.**
**Phase 2, step 2 — high-impact network gaps: complete and validated.**
**Phase 2, step 4 — targeted marine-intake evidence resolution: complete.**
**Phase 2, step 5 — network connectivity finalisation + computed route layer: complete.**
`PL001` and `PL005` are formally scored `PARTIALLY RESOLVED` — see
[`docs/data_sources.md`](docs/data_sources.md#targeted-marine-intake-evidence-resolution-phase-2-step-4).
See [`docs/phase2_report.md`](docs/phase2_report.md) for the full Phase 2
summary and [`docs/network_connectivity_report.md`](docs/network_connectivity_report.md)
for the graph analysis.

What exists is the *India Energy Network Reference Layer* — source-backed
reference datasets describing the fixed entities of India's crude supply
chain — the **edge** layer connecting them, a first **computed/derived**
layer estimating route distances from that graph, a validation suite that
asserts the integrity of all three, and (new) an MVP demonstration dashboard
that reads and visualizes this data — see "MVP Demo Dashboard" below. No API,
database schema, agent, forecasting model, or optimisation engine has been
written — those are deliberately out of scope until the data underneath them
is trustworthy.

**Reference data and processed data are kept strictly separate.**
`data/reference/` holds only source-backed facts; `data/processed/` holds
only values computed from those facts (currently: geodesic route distances),
each carrying its own `distance_method`/`computed_at`. Neither is ever mixed
into the other — see `docs/data_dictionary.md`'s "REFERENCE DATA vs PROCESSED
DATA" section.

| | |
| --- | --- |
| Reference datasets | 13 files, 206 data rows |
| Processed (computed) datasets | 2 files, 16 data rows |
| Validators | 14 scripts (11 reference-dataset validators + network-link + computed-route + Phase 1 suite runner) |
| Phase 1 validation | **PASS** — 10/10 validators, 0 critical failures |
| Phase 2 validation | **PASS** — 21 network links, 5 pipelines, 9 computed routes, 7 computed segments, 0 critical failures |
| Application code | none yet |
| Dependency manifest | none — validators use the Python standard library only |
| Tests | none beyond the validators |

## Repository layout

Directories not listed under `data/` or `docs/` are placeholders for the
intended architecture and are still empty.

```
agents/         Autonomous / LLM agents for monitoring and scenario reasoning
backend/        API service layer
dashboard/      User-facing UI (Streamlit is the assumed target — see .gitignore)
data/
  raw/          Unmodified source downloads
  processed/    Cleaned, analysis-ready derivatives
  reference/    Curated master data
  validation/   Data-quality validators
database/       Schema definitions and migrations
docs/           Design notes and documentation
models/         Forecasting / risk models
notebooks/      Exploratory analysis
optimization/   Network flow and re-routing solvers
tests/          Test suite
```

## Data

Every dataset carries per-row provenance (`source`, `source_url`,
`report_date` / `effective_date`, `retrieved_at`) so figures stay auditable and
refreshes are traceable.

Full documentation:

- [`docs/data_dictionary.md`](docs/data_dictionary.md) — every column, unit,
  allowed value and caveat
- [`docs/data_sources.md`](docs/data_sources.md) — source hierarchy, documented
  source conflicts, staleness
- [`docs/phase1_report.md`](docs/phase1_report.md) — what was built, what was
  not, and why
- [`docs/phase2_report.md`](docs/phase2_report.md) — Phase 2 steps 1–5 summary
- [`docs/network_connectivity_report.md`](docs/network_connectivity_report.md)
  — connected components and isolated nodes in the reference network graph

### Datasets — REFERENCE (`data/reference/`, source-backed)

| Dataset | File | Rows | Primary source | Effective | Validation |
| --- | --- | ---: | --- | --- | --- |
| Refinery master | `data/reference/refineries.csv` | 24 | PPAC — Installed Refining Capacity | 2026-04-01 | PASS |
| Strategic reserves | `data/reference/strategic_reserves.csv` | 5 | PIB / MoPNG; ISPRL | 2025-03-20 | PASS |
| Ports | `data/reference/ports.csv` | 18 | MoPNG-PS&W; port authorities; GMB | 2025-03-31 | PASS |
| Suppliers / origins | `data/reference/suppliers.csv` | 10 | UN M49; OFAC | 2026-08-23 | PASS |
| Crude grades | `data/reference/crude_grades.csv` | 14 | EIA; ADNOC | 2024 | PASS |
| Chokepoints | `data/reference/chokepoints.csv` | 7 | EIA | 2016–2024 | PASS |
| Trade corridors | `data/reference/routes.csv` | 8 | **Modelled** (nodes sourced) | 2026-08-23 | PASS |
| Corridor nodes | `data/reference/route_nodes.csv` | 42 | **Modelled** (nodes sourced) | 2026-08-23 | PASS |
| Sanctions reference | `data/reference/sanctions.csv` | 8 | OFAC; UN SC; EU | 2026-08-23 | PASS |
| Energy price reference | `data/reference/energy_prices_reference.csv` | 5 | EIA; PPAC | 2026-08-23 | PASS |
| Source registry | `data/reference/source_registry.csv` | 41 | — (index) | 2026-08-23 | PASS |
| Crude pipelines *(Phase 2)* | `data/reference/pipelines.csv` | 5 | IndianOil; BPCL; HMEL | 2026-08-23 | PASS |
| Network links *(Phase 2-3)* | `data/reference/network_links.csv` | 23 | Operator, port-authority and MoEFCC documents | 2026-08-23 | PASS |

### Datasets — PROCESSED (`data/processed/`, computed/modelled)

| Dataset | File | Rows | Computed from | Method | Validation |
| --- | --- | ---: | --- | --- | --- |
| Computed routes *(Phase 2, step 5)* | `data/processed/computed_routes.csv` | 9 | `routes.csv`, `route_nodes.csv`, `ports.csv`, `chokepoints.csv` | Geodesic (haversine) distance, partial-chain only | PASS |
| Route segments *(Phase 2, step 5)* | `data/processed/route_segments.csv` | 7 | `ports.csv`, `chokepoints.csv` coordinates | Geodesic (haversine) distance, `R = 6371.0088 km` | PASS |

**REFERENCE vs PROCESSED is a mandatory distinction in this repository.** A
reference row states "a source published X." A processed row states "a
stated method computed Y from sourced inputs." Neither may be substituted for
the other, and `validate_computed_routes.py` fails if a computed value is
ever found written back into `data/reference/routes.csv`.

### Caveats you must read before using any of this

These are properties of the sources, not defects to be fixed:

**Refineries** (unchanged from the original documentation)

- `state` reflects PPAC's own labelling, which is not strictly state-level — the
  two CPCL entries are listed under `CHENNAI` rather than Tamil Nadu.
- `CPCL, Cauvery Basin` is recorded at `0.0` MMTPA (not in operation).
- Capacity is *installed* capacity, not actual throughput.
- Total installed capacity is **267.116 MMTPA** across 24 refineries.

**Strategic reserves**

- Figures are **storage capacity, never inventory**. No fill level is recorded,
  and days-of-cover must not be derived from capacity alone.
- Phase II facilities (Chandikhol, Padur II) are **approved, not built**, and
  must not be counted as available storage.
- ISPRL and PIB **disagree** on the Phase I total (5.03 vs 5.33 MMT). Both are
  documented; the dataset follows PIB's internally consistent per-location split.
- Facility coordinates are NULL — ISPRL does not publish them.

**Ports**

- 10 of 18 ports have `crude_handling = unknown`. That means *no authoritative
  statement was found* — it is **not** a finding of "no".
- Coordinates are **locality centroids from OpenStreetMap, not berth positions**.
- No handling capacity is recorded anywhere; none was sourced.

**Crude grades**

- Saudi grades are published as **ranges**, stored verbatim. No midpoints exist.
- Brent, WTI, Dubai and Oman have **NULL** API/sulfur — EIA publishes those
  numbers only inside chart images, which were not transcribed.
- **Urals and ESPO are absent.** No authoritative assay was obtained.

**Chokepoints**

- There is deliberately **no risk score** here. This table holds historical
  baselines only; current geopolitical risk belongs to a later dynamic layer.
- Suez, SUMED and Malacca baselines are from **2016** and are stale.
- Bab el-Mandeb and Cape of Good Hope figures cover a **partial year**
  (Jan–Aug 2024) and are not comparable with full-year figures.
- The Turkish Straits have **no flow figure** — a gap, not a zero.

**Corridors**

- `routes.csv` and `route_nodes.csv` are **modelled**, not observed. They assert
  a plausible routing exists, nothing about volume or current availability.
- Distance and transit time are **NULL on every route** — to be modelled later.
- RT005 (Russia) and RT008 (United States) have **no corridor evidence**.

**Sanctions**

- **Not a screening list.** Screen against the authority's own current list at
  the time of the transaction. No designated party is stored here.
- `no_ofac_country_program_listed` does **not** mean "no sanctions exposure".

**Energy prices**

- **No price value is stored anywhere in this repository** — only series
  definitions.

**Network links** *(Phase 2, steps 1–2)*

- An edge asserts that a **sourced connection exists**. It asserts nothing
  about volume, throughput, current utilisation, or ownership of the shared
  asset. Reserve edges carry **no inventory or fill-level claim**.
- **No edge is created from geography.** Endpoints are matched by company and
  published record name; `validate_network_links.py` rejects any row containing
  inference wording.
- **The absence of an edge is not evidence that no connection exists.** Every
  candidate edge investigated and deliberately not created is listed in
  [`docs/data_sources.md`](docs/data_sources.md), with the reason.
- Two of five pipelines (`PL001` Salaya–Mathura, `PL005` Vadinar–Bina) have
  **no sourced marine intake**: their coastal termini could not be resolved to
  a port record. Steps 2 and 4 re-investigated both and closed neither to a
  port endpoint — each is formally scored `PARTIALLY RESOLVED`: the
  operational relationship at Vadinar is established for both, but the
  specific port record is not.
- Several edges carry an **in-row caveat** that survives into any downstream
  use: `NL011` / `NL012` (Paradip SPM ownership unresolved), `NL014` (the
  0.3 MMT commercial compartment only), `NL016` (indirect), `NL018` (evidenced
  from the port side only), `NL019` (no SPM ownership asserted), `NL021`
  (jurisdictional conflict between the operator's filing and `PORT002`'s own
  Phase 1 note).

**Computed routes** *(Phase 2, step 5)*

- **No route has a computed distance covering its full origin-to-destination
  span.** `suppliers.csv` and every named export terminal carry no
  coordinate, so a distance can only ever be computed for the last,
  coordinate-resolvable leg into India — `distance_coverage =
  partial_last_leg_only` says this on every populated row. Three routes
  (`RT002`, `RT005`, `RT008`) have no computable segment at all.
- **Every computed distance is geodesic (great-circle), never a maritime
  sailing distance.** It does not follow a shipping lane, a canal, or avoid
  land, and must never be presented as one.
- **No vessel-speed or transit-time assumption exists.**
  `estimated_transit_days` is `NULL` on every row of `computed_routes.csv`,
  for the same reason it is `NULL` on every row of `routes.csv`.
- **`RT004`'s `via_suez` and `via_sumed` variants are not comparable.**
  `via_sumed`'s figure omits an entire leg because `CP004` (the SUMED
  pipeline) has no sourced coordinate — it is smaller for a structural
  reason, not because that routing is actually shorter.
- Full column documentation: `docs/data_dictionary.md` §§13–14. Sourcing
  rationale: `docs/data_sources.md`
  ("Network connectivity finalisation and the computed route layer").

## MVP Demo Dashboard

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

This MVP demonstrates the currently implemented reference-network and
scenario-analysis layers. Live geopolitical feeds, maritime intelligence,
forecasting, procurement optimization and autonomous AI agents are planned
future layers and are not represented as operational functionality in this
demo.

The dashboard reads directly from `data/reference/` and `data/processed/` —
every KPI, table, and map marker is computed at run time, not hardcoded.
See [`dashboard/README.md`](dashboard/README.md) for the screen list, and
[`docs/demo_script.md`](docs/demo_script.md) /
[`docs/presentation_outline.md`](docs/presentation_outline.md) for the
video/presentation materials built around it.

## Validation

```bash
python data/validation/validate_phase1.py             # Phase 1 suite, full output
python data/validation/validate_phase1.py --quiet     # summary table only
python data/validation/validate_network_links.py      # Phase 2 edge layer
python data/validation/validate_computed_routes.py    # Phase 2 computed route layer
python data/validation/validate_network_connectivity.py  # graph analysis (reporting, not pass/fail)
```

`validate_phase1.py` runs the Phase 1 datasets only, and is deliberately left
that way so the Phase 1 result stays a fixed, re-checkable baseline. The
network-link and computed-route validators are run separately.
`validate_network_connectivity.py` is a reporting tool, not a pass/fail gate —
see [`docs/network_connectivity_report.md`](docs/network_connectivity_report.md).

Exits `0` only if every validator passes. Individual validators can be run
directly. All are **read-only** and never modify a source file. Requires Python
3.8+ and **no third-party packages**.

See [`data/validation/README.md`](data/validation/README.md) for what each
validator checks and what counts as a critical failure.

## License

[MIT](LICENSE)
