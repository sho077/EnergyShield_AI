# Data Sources

Every figure in `data/reference/` traces to a source recorded here and in
`data/reference/source_registry.csv`. This document explains the sourcing
*policy*; the registry is the machine-readable index.

## Source hierarchy

| Level | Meaning | Used for |
| --- | --- | --- |
| `official_india` | PPAC, MoPNG, ISPRL, PIB, port authorities, Gujarat Maritime Board | All India-specific facts |
| `official_international` | EIA, UN, OFAC, national oil companies publishing their own product specs | Global chokepoints, crude assays, sanctions programs, benchmarks |
| `authoritative_public` | OpenStreetMap / Nominatim | Coordinates only |
| `commercial` | — | **Not used as a primary source anywhere in Phase 1** |
| `secondary` | This project's own modelling | `routes.csv`, `route_nodes.csv` only |

An official value is never silently replaced by a commercial estimate. Where
the only available figure came from a commercial provider *through* an official
publisher, the row records that explicitly — see **Vortexa** below.

## Rules applied throughout

1. **Nothing is invented.** No number appears in any dataset unless a source
   printed it. Where a value was unavailable it is `NULL` (an empty field) and
   the row's `notes` say why.
2. **Verbatim where it matters.** Rows asserting a material fact quote the
   source sentence in `notes`. `validate_ports.py` enforces this for every
   `crude_handling = yes` row.
3. **No derived values presented as sourced.** Ranges are never collapsed to
   midpoints; classifications are never inferred from thresholds.
4. **Numbers inside chart images are not transcribed.** Several EIA pages state
   a classification in text but publish the API/sulfur numbers only in a chart.
   Those rows carry `NULL` assay values rather than an eyeballed figure.
5. **Coordinates carry separate provenance.** `coordinate_source` /
   `coordinate_source_url` are distinct columns because the geolocation and the
   factual claim come from different publishers.
6. **Blank means NULL**, consistently, in every dataset.

## Documented source conflicts

### Strategic reserve Phase I total — 5.03 vs 5.33 MMT

| Source | Figure |
| --- | --- |
| [ISPRL, *About Us*](https://www.isprlindia.com/aboutus.asp) | "the strategic storage capacity was enhanced to **5.03 MMT**" |
| [PIB / MoPNG, 20 Mar 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2113233) | "total capacity of **5.33** Million Metric Tonnes … Vishakhapatnam (1.33 MMT), Mangaluru (1.5 MMT) and Padur (2.5 MMT)" |

`strategic_reserves.csv` follows **PIB**, because PIB publishes a per-location
split that is internally consistent (1.33 + 1.5 + 2.5 = 5.33) whereas ISPRL's
5.03 does not reconcile with its own narrative (a 5.0 MMT programme with
Visakhapatnam raised to 1.33 MMT gives 5.33, not 5.03). Both figures are
preserved: the ISPRL value is recorded here and re-stated as a warning on every
run of `validate_strategic_reserves.py`. Neither was averaged.

### Arabian Extra Light API range — 36–40 vs 37–40

| Source | Figure |
| --- | --- |
| EIA Country Analysis Brief: Saudi Arabia, Table 2 (data source: Saudi Aramco) | 37 to 40 |
| Aramco regional news page describing the same grade | 36 to 40 |

`crude_grades.csv` (CG007) stores the formally tabulated `37 to 40` and records
the other figure in `notes`. Neither was averaged.

## Commercial data reaching us through an official publisher

Three chokepoint flow figures (Hormuz, Bab el-Mandeb, Cape of Good Hope) are
**Vortexa tanker-tracking data published by EIA**. EIA is the publisher; Vortexa
is the data collector. Each affected row records this in `flow_data_origin`, so
downstream work can tell an EIA-collected statistic from a commercially
collected one that EIA republished.

## Known staleness

`chokepoints.csv` mixes vintages, and the column `flow_period` always says
which:

| Chokepoint | Flow period | Note |
| --- | --- | --- |
| Strait of Hormuz | 2024 | Current |
| Bab el-Mandeb | Jan–Aug 2024 | **Partial year** |
| Cape of Good Hope | Jan–Aug 2024 | **Partial year** |
| Suez Canal | 2016 | Stale — refresh required |
| SUMED Pipeline | 2016 | Stale — refresh required |
| Strait of Malacca | 2016 | Stale — refresh required |
| Turkish Straits | — | **No figure obtainable** |

Partial-year and full-year figures must not be compared without adjustment;
`validate_chokepoints.py` flags every partial period on each run.

## Modelled corridors

`routes.csv` and `route_nodes.csv` are the only datasets in the reference layer
that are **not** sourced observations. Their `source_url` is the repo-relative
reference `docs/data_sources.md#modelled-corridors`, which points here, and
their registry entry (`SRC027`) is deliberately recorded at `secondary`
authority level.

What this means precisely:

* A route asserts that a **plausible physical routing exists** between its
  ordered nodes. It asserts nothing about volume, frequency, commercial
  availability, or whether any cargo currently moves on it.
* The **nodes are sourced**. Every `origin_supplier_id`, `destination_port_id`
  and chokepoint reference is a foreign key into `suppliers.csv`, `ports.csv`
  or `chokepoints.csv`, and `validate_routes.py` fails if any does not resolve.
* `estimated_distance_km` and `estimated_transit_days` are **NULL on every
  route**, and the validator fails if either is ever populated. Phase 1 sourced
  no transit figures; a plausible-looking estimate here would be
  indistinguishable from a real one downstream.
* Where external evidence for a corridor does exist it is recorded separately in
  `corridor_evidence` / `corridor_evidence_url` — six of eight routes have it.
  **RT005 (Russia → India) and RT008 (United States → India) have none**, and
  both are flagged in-row as requiring Phase 2 resolution into distinct
  routings.

Destination ports are a **modelling choice**, not a property of the corridor: a
representative Indian crude-receiving port was selected from `ports.csv`, and
the validator enforces that it is one whose `crude_handling` is `yes`.

## Raw source material

Archived under `data/raw/`, separate from curated data in `data/reference/`:

```
data/raw/isprl/   ISPRL About Us pages, retrieved 2026-08-23
data/raw/pib/     PIB press releases PRID 2113233 and 1739019
```

Large PDFs (the MoPNG-PS&W Annual Report, EIA country analyses) were read during
collection but are **not** committed, to keep the repository small. Each is
reachable from its `source_url` in the registry.
