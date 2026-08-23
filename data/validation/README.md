# Data Validation

Reusable data-quality checks for the EnergyShield-AI reference datasets.

Twelve scripts live here: one validator per reference dataset, plus
`validate_phase1.py`, which runs the Phase 1 validators and returns a single
PASS/FAIL.

| Script | Dataset |
| --- | --- |
| `validate_phase1.py` | **runs every Phase 1 validator below** |
| `validate_refineries.py` | `refineries.csv` |
| `validate_strategic_reserves.py` | `strategic_reserves.csv` |
| `validate_ports.py` | `ports.csv` |
| `validate_suppliers.py` | `suppliers.csv` |
| `validate_crude_grades.py` | `crude_grades.csv` |
| `validate_chokepoints.py` | `chokepoints.csv` |
| `validate_routes.py` | `routes.csv` + `route_nodes.csv` |
| `validate_sanctions.py` | `sanctions.csv` |
| `validate_energy_prices_reference.py` | `energy_prices_reference.csv` |
| `validate_source_registry.py` | `source_registry.csv` |
| `validate_network_links.py` *(Phase 2)* | `network_links.csv` + `pipelines.csv` |
| `validate_computed_routes.py` *(Phase 2, step 5)* | `data/processed/computed_routes.csv` + `data/processed/route_segments.csv` |
| `validate_network_connectivity.py` *(Phase 2, step 5, reporting only)* | Connectivity of `refineries.csv` + `ports.csv` + `strategic_reserves.csv` + `pipelines.csv` via `network_links.csv` |

`_common.py` holds the shared `Report` class, CSV loader and generic checks
(schema, identifiers, required fields, numerics, coordinates, provenance,
controlled vocabularies, referential integrity).

**`validate_refineries.py` deliberately does not import `_common.py`.** It was
written and independently validated before the shared module existed, and is
left byte-for-byte untouched so that its result stays independent of later work.

## Running them

From the repository root — the whole suite:

```bash
python data/validation/validate_phase1.py            # full output
python data/validation/validate_phase1.py --quiet    # summary table only
```

The suite runs each validator as a **separate process**, so one crashing cannot
take the others down, and exits `0` only if every validator exits `0`. It also
compares `refineries.csv` against a recorded SHA-256 baseline as a tamper hint.

`validate_network_links.py` is **not** part of that suite and is run
separately:

```bash
python data/validation/validate_network_links.py
```

It is kept out deliberately, so the Phase 1 result stays a fixed baseline that
later phases can be regression-tested against rather than silently redefined.
What it enforces, beyond the generic checks, is that **an edge is anchored to a
record and never to a place**: both endpoints must resolve by id *and* their
stored names must match the reference record character for character;
`link_type` must agree with the endpoint types; `notes` must open `Evidence: `
and say what the source `Establishes: `; and no field may contain inference
wording (`proximity`, `nearby`, `assumed`, `presumably`, …).

The computed-route validator runs the same way and is also kept out of the
Phase 1 suite:

```bash
python data/validation/validate_computed_routes.py
```

Beyond the generic checks, it verifies that the computed layer in
`data/processed/` stays reproducible and separate from `data/reference/`:
every `route_id` resolves against `routes.csv`; every node id resolves
against the reference dataset its prefix implies; no distance is negative or
zero; every populated value carries a stated method; `routes.csv` still
carries no distance/transit value of its own; there are no duplicate
route/segment combinations; and — the check that matters most for a computed
dataset — every `geodesic_haversine_r6371.0088km` segment is **independently
recomputed** from `ports.csv`/`chokepoints.csv` coordinates and must match
the stored value within 0.5 km.

`validate_network_connectivity.py` is different in kind from every other
script here: it is a **reporting tool, not a pass/fail gate**. It prints node
and edge counts by type, connected components, and the isolated-node list
from the reference network graph. It never fails on an isolated node, because
an isolated node is very often the correct, honest state of a sourced graph —
see `docs/network_connectivity_report.md` for the curated write-up of its
output.

Or a single dataset:

```bash
python data/validation/validate_refineries.py
```

The dataset path defaults to `data/reference/refineries.csv`, resolved relative
to the script itself, so the command works from any working directory. To point
it at a different copy (for example when testing a candidate refresh):

```bash
python data/validation/validate_refineries.py --csv path/to/refineries.csv
```

### Requirements

Python 3.8 or newer. **No third-party packages.** The project has no dependency
manifest yet, so the validator is written against the standard library only
(`csv`, `decimal`, `re`, `datetime`) rather than pandas. This keeps it runnable
on a bare interpreter and deterministic across machines. If the project later
adopts a dependency strategy, this choice can be revisited.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | All critical checks passed. Warnings may still be present. |
| `1` | At least one **critical** check failed. |
| `2` | The dataset could not be read at all (missing file, unreadable, no header). |

The script is **read-only** and never modifies the source CSV.

## What it checks

### A. Schema
- All nine documented columns are present.
- No unexpected or duplicate columns.
- Column names carry no stray whitespace; column order matches the README.
- Every row has exactly one value per column (no ragged rows).

### B. Row integrity
- Row count matches the documented total.
- No duplicate `refinery_id`.
- No duplicate `refinery_name`.
- No blank or null values in any required field.

### C. Numeric validation (`capacity_mmtpa`)
- Every value parses as a number.
- No negative values.
- Zero-capacity records are counted and listed **separately** — they are
  legitimate records, not errors.
- Total installed capacity is summed with `Decimal` (exact, no float drift) and
  compared against the documented PPAC figure of **267.116 MMTPA**, tolerance
  ±0.001.

### D. Provenance
- Every row carries `source`, `source_url`, `report_date`, `retrieved_at`.
- `source_url` is uniform across rows, uses `https://`, and matches the URL
  documented in the top-level README.
- `source` description is uniform across rows.
- Both date columns are valid ISO-8601 (`YYYY-MM-DD`).
- `retrieved_at` is on or after `report_date`.

### E. Identifiers
- `refinery_id` matches the `R###` format.
- IDs are unique.
- IDs form a gapless `R001..RNNN` sequence, and rows are stored in ascending
  ID order.
- **IDs are never renamed or renumbered by this script.** Gaps are reported for
  a human to decide on.

### F. Text quality
- Leading/trailing whitespace in any field.
- Refinery names that collide after normalisation (suspicious near-duplicates).
- The same company appearing under conflicting spellings.
- Mixed capitalisation conventions in `company`.
- Source footnote markers (`*`) in names are reported and **preserved verbatim**.

### G. Documented source caveats
Each caveat recorded in the top-level README is asserted explicitly, so a future
data refresh cannot silently drop it:

- State labels that are not conventional Indian state/UT names are flagged.
- The zero-capacity `CPCL, Cauvery Basin` record must still be present. Its
  absence is a **critical failure** — zero-capacity records are retained, never
  deleted.
- A reminder that `capacity_mmtpa` is *installed* capacity, not throughput.

## What counts as a critical failure

A critical failure exits non-zero and blocks downstream use of the dataset:

- Any expected column missing, or an unexpected/duplicate column present.
- Ragged rows, or whitespace in header names.
- Row count differing from the documented total.
- Duplicate `refinery_id` or `refinery_name`.
- Any blank/null in a required field.
- `capacity_mmtpa` non-numeric or negative.
- Total capacity outside ±0.001 of the documented PPAC figure.
- Any row missing provenance.
- Malformed `report_date` / `retrieved_at`.
- `refinery_id` not matching `R###`, or not unique.
- The zero-capacity Cauvery Basin record being absent.

Everything else is a **warning**: reported, reviewed, but non-blocking. Warnings
mostly capture how the source itself is published, and correcting them would
mean diverging from PPAC.

## Known source caveats

These are properties of the PPAC source data, **not** defects to be fixed. They
are expected to appear as warnings on every run:

1. **Non-conventional state labels.** The two CPCL entries (`R015`, `R016`) are
   listed under `CHENNAI`, a city, rather than Tamil Nadu. Left as published.
2. **Zero-capacity record.** `R016 CPCL, Cauvery Basin*` is recorded at
   `0.0` MMTPA (not in operation). It is a valid non-operating record and must
   be retained, not deleted. It is included in the row count and
   contributes zero to the capacity total.
3. **Footnote marker.** `R016`'s name ends in `*`, a footnote marker carried
   over from the PPAC table. Preserved verbatim rather than stripped.
4. **Mixed capitalisation.** Ten company names are upper-case as published;
   `HPCL Rajasthan Refinery Limited` is title-case. Left as published, since
   normalising would diverge from the source.
5. **Punctuation inconsistency.** `R015` is named `CPCL,Manali` with no space
   after the comma, while `R016` uses `CPCL, Cauvery Basin*`. This mirrors the
   source and is not auto-corrected.
6. **Installed capacity is not throughput.** `capacity_mmtpa` is nameplate
   installed capacity. It must not be used as a proxy for actual processed
   volume in any downstream model.

## Conventions for future datasets

- Carry per-row provenance (`source`, `source_url`, `report_date`,
  `retrieved_at`) on every reference dataset.
- Never silently "correct" source values. If a value looks wrong, flag it as
  uncertain and verify against the publisher before changing anything.
- Add a matching `validate_<dataset>.py` here when a new reference dataset
  lands, following the same PASS/FAIL and exit-code contract, and register it in
  `validate_phase1.py`.
- Build it on `_common.py` rather than copying checks, and add dataset-specific
  checks for whatever that dataset can get *silently* wrong.

## What the Phase 1 validators guard against

Beyond generic hygiene, each validator asserts the specific failure mode that
would quietly corrupt its dataset:

| Dataset | The thing that must not happen |
| --- | --- |
| `strategic_reserves` | Storage capacity being read as inventory, or approved-but-unbuilt Phase II capacity being counted as available |
| `ports` | A `crude_handling = yes` without a verbatim source quote; a constituent terminal being summed with its parent; any unsourced capacity column |
| `crude_grades` | A published *range* being collapsed to a midpoint; an unexplained missing assay |
| `suppliers` | The reference list acquiring a volume, share, price or ranking column |
| `chokepoints` | A risk score entering the reference layer; a flow figure without its period; capacity stored as throughput |
| `routes` | A modelled corridor being mistaken for an observation; an invented distance or transit time; a node that resolves to nothing |
| `sanctions` | The file being usable as a screening list; a designated party or legal determination being stored |
| `energy_prices_reference` | A price value being cached in a definition file |
| `source_registry` | A dataset with no registry entry, or a registry entry pointing at nothing |

Several of these fired during Phase 1 construction and forced corrections —
notably `validate_ports.py` rejecting an inferred `crude_handling = yes` for
Cochin Port that no source actually stated.
