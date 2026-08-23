# EnergyShield-AI

AI-Driven Energy Supply Chain Resilience Platform for India.

The goal is a decision-support system that models India's downstream petroleum
supply chain — refineries, transport links, and demand centres — and answers
resilience questions against it: if a node or corridor goes down, what capacity
is at risk, which regions are exposed, and how should flows be re-routed?

## Status

**Current phase: Phase 1 — Data Foundation. Complete and validated.**

There is still no runnable application. What exists is the *India Energy
Network Reference Layer*: ten source-backed reference datasets, a validation
suite that asserts their integrity, and the documentation needed to trust them.
No dashboard, API, database schema, agent, forecasting model, or optimisation
engine has been written — those are deliberately out of scope until the data
underneath them is trustworthy.

| | |
| --- | --- |
| Reference datasets | 10 files, 168 data rows |
| Validators | 11 scripts (10 dataset validators + 1 suite runner) |
| Validation status | **PASS** — 10/10 validators, 0 critical failures |
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

### Datasets

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
| Source registry | `data/reference/source_registry.csv` | 27 | — (index) | 2026-08-23 | PASS |

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

## Validation

```bash
python data/validation/validate_phase1.py            # full output
python data/validation/validate_phase1.py --quiet    # summary table only
```

Exits `0` only if every validator passes. Individual validators can be run
directly. All are **read-only** and never modify a source file. Requires Python
3.8+ and **no third-party packages**.

See [`data/validation/README.md`](data/validation/README.md) for what each
validator checks and what counts as a critical failure.

## License

[MIT](LICENSE)
