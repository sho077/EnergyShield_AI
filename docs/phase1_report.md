# Phase 1 Report — India Energy Network Reference Layer

**Date:** 2026-08-23
**Result:** **PASS** — 10/10 validators, 0 critical failures
**Scope boundary:** Phase 1 only. No Phase 2 work was started.

---

## 1. Scope

Phase 1 built the *India Energy Network Reference Layer*: auditable,
source-backed reference datasets describing the fixed entities of India's crude
supply chain, plus the tooling to prove they are internally consistent.

**In scope and delivered:** refineries (pre-existing), strategic reserves, ports,
suppliers/origins, crude grades, chokepoints, trade corridors, sanctions
reference, energy price reference, source registry, validation tooling,
documentation.

**Deliberately not built:** dashboard, backend API, database schema, agents,
forecasting models, optimisation engine. Confirmed empty at the end of the phase.

---

## 2. Datasets created

| # | Dataset | File | Rows | Cols | Primary source | Authority |
| --- | --- | --- | ---: | ---: | --- | --- |
| 0 | Refinery master | `data/reference/refineries.csv` | 24 | 9 | PPAC — Installed Refining Capacity (Apr 2026) | official_india |
| 1 | Strategic reserves | `data/reference/strategic_reserves.csv` | 5 | 20 | PIB/MoPNG PRID 2113233; ISPRL | official_india |
| 2 | Ports | `data/reference/ports.csv` | 18 | 23 | MoPNG-PS&W AR 2024-25; port authorities; GMB | official_india |
| 3 | Suppliers / origins | `data/reference/suppliers.csv` | 10 | 15 | UN M49; OFAC programs index | official_international |
| 4 | Crude grades | `data/reference/crude_grades.csv` | 14 | 15 | EIA Iraq & Saudi Arabia briefs; ADNOC | official_international |
| 5 | Chokepoints | `data/reference/chokepoints.csv` | 7 | 19 | EIA Today in Energy (5 articles) | official_international |
| 6a | Trade corridors | `data/reference/routes.csv` | 8 | 19 | **Modelled**; nodes sourced | secondary |
| 6b | Corridor nodes | `data/reference/route_nodes.csv` | 42 | 9 | **Modelled**; nodes sourced | secondary |
| 7 | Sanctions reference | `data/reference/sanctions.csv` | 8 | 15 | OFAC; UN Security Council; EU Sanctions Map | official_international |
| 8 | Energy price reference | `data/reference/energy_prices_reference.csv` | 5 | 16 | EIA series; PPAC | mixed |
| 9 | Source registry | `data/reference/source_registry.csv` | 27 | 11 | — (index of all of the above) | — |

**Total: 168 data rows across 11 files.** Dataset 0 pre-existed and was **not
modified** (verified byte-for-byte, MD5 `94bfdd9a967a14d185e872950364e543`,
SHA-256 `42478cc9…199dee`).

## 3. Tooling and documentation created

| File | Purpose |
| --- | --- |
| `data/validation/_common.py` | Shared `Report` class, CSV loader, generic checks |
| `data/validation/validate_strategic_reserves.py` | + 8 more per-dataset validators |
| `data/validation/validate_phase1.py` | Suite runner, one overall PASS/FAIL |
| `docs/data_dictionary.md` | Every column, unit, allowed value, caveat |
| `docs/data_sources.md` | Source hierarchy, conflicts, staleness, modelling policy |
| `docs/phase1_report.md` | This file |
| `README.md` | Updated to reflect Phase 1 |
| `data/validation/README.md` | Updated for the full validator suite |
| `data/raw/isprl/`, `data/raw/pib/` | Archived raw source pages |

---

## 4. Validation results

```
dataset                      result  critical  warnings
--------------------------------------------------------
refineries                     PASS         0         2
strategic_reserves             PASS         0         1
ports                          PASS         0         0
crude_grades                   PASS         0         1
suppliers                      PASS         0         0
chokepoints                    PASS         0         1
routes                         PASS         0         0
sanctions                      PASS         0         0
energy_prices_reference        PASS         0         0
source_registry                PASS         0         0

validators run    : 10
validators passed : 10
PHASE 1 RESULT: PASS
```

The five warnings are all **documented source behaviour**, not defects: two are
the PPAC quirks recorded against the refinery dataset, one is the ISPRL/PIB
capacity conflict, one is the Arabian Extra Light range conflict, and one is the
staleness flag on three chokepoint baselines.

### Independent cross-checks performed

| Check | Result |
| --- | --- |
| Refinery installed capacity sums to PPAC's published 267.116 MMTPA | ✅ exact |
| SPR Phase I: 1.33 + 1.5 + 2.5 = 5.33 MMT, matching PIB's stated total | ✅ exact |
| SPR Phase II: 4.0 + 2.5 = 6.5 MMT, matching the July 2021 Cabinet approval | ✅ exact |
| SPR figures corroborated across two independent PIB releases (2021, 2025) | ✅ agree |
| Operational Major Ports = 12, matching MoPNG-PS&W's own statement | ✅ exact |
| Notified-not-operational Major Ports = 2 (14 notified − 12 operational) | ✅ exact |
| EIA Saudi grade reserve shares sum to 100% (35+17+34+13+1) | ✅ exact |
| Every route node resolves against its reference dataset | ✅ 42/42 |
| Every `source_url` in every dataset is declared in the registry | ✅ complete |
| Every reference CSV on disk has a registry entry, and vice versa | ✅ both ways |

### Defects the validators caught and forced fixed

1. **Cochin Port** was drafted with `crude_handling = yes`, inferred from the
   presence of an SPM. `validate_ports.py` rejected it because no source states
   crude. Corrected to `unknown`. *This is the single most important thing the
   tooling did — it caught an inference dressed as a fact.*
2. **Vadinar Offshore Oil Terminal** asserted crude handling without a verbatim
   quote in `notes`. The quote was added.
3. **Haldia Dock Complex** lacked the double-counting warning required of a
   constituent dock. Added.
4. **Strait of Hormuz** discussed bypass-pipeline capacity without stating that
   the stored flow figure is throughput. Disambiguated.

---

## 5. Unresolved limitations

Ordered by how much they constrain Phase 2.

### High impact

| # | Limitation | Effect |
| --- | --- | --- |
| L1 | **10 of 18 ports have `crude_handling = unknown`** — including Chennai, Kamarajar, VOC, JNPA, Mormugao, Cochin, SMP Kolkata and Haldia | The port layer cannot yet answer "which ports can receive crude" completely. `unknown` ≠ `no`. |
| L2 | **No Urals or ESPO crude grade** | Russia is a major origin with no grade record at all, so no refinery-compatibility modelling can include Russian crude. |
| L3 | **No Dubai/Oman price provider** | The benchmark Saudi Aramco uses for Asian sales has no machine-readable official series identified. |
| L4 | **RT005 (Russia) and RT008 (US) have no corridor evidence** and no determined chokepoint set | Both can reach India by materially different paths; unusable in a flow model until split. |
| L5 | **No per-port handling capacity anywhere** | Capacity-constrained rerouting cannot be modelled at the port level. |

### Medium impact

| # | Limitation | Effect |
| --- | --- | --- |
| L6 | **Turkish Straits have no flow baseline** | One of the seven required chokepoints has no volume. EIA publishes it only in chart images. |
| L7 | **Suez, SUMED, Malacca baselines are from 2016** | Nine years stale; almost certainly unrepresentative. |
| L8 | **Bab el-Mandeb / Cape of Good Hope are partial-year (Jan–Aug 2024)** | Not comparable with full-year figures without adjustment. |
| L9 | **All SPR facilities have NULL coordinates** | Strategic reserves cannot be placed on a map or distance-modelled. |
| L10 | **All port and chokepoint coordinates are locality centroids** | Adequate for regional topology, not for berth- or lane-level work. |

### Lower impact

| # | Limitation |
| --- | --- |
| L11 | No export ports or crude grades sourced for Kuwait, Nigeria, Angola, Brazil, Canada |
| L12 | Brent/WTI/Dubai/Oman have NULL API and sulfur (EIA publishes them only in chart images) |
| L13 | PPAC price series frequency and start date unknown (JavaScript-delivered tables) |
| L14 | `refinery_connected` / `pipeline_connected` / `storage_connected` are `unknown` for most ports |
| L15 | Saudi Gulf-coast export terminals are unnamed in the sources consulted (only Yanbu is named) |

### Deliberate non-collection

These were **not** collected on purpose, and should stay uncollected:

- **Sanctions screening lists** (OFAC SDN, UN Consolidated, EU Consolidated). A
  partial, version-controlled copy of a screening list is worse than none: it
  looks usable and is silently stale. Only authority and program pointers are
  stored.
- **Any price value.** A cached price is stale on write.
- **Any inventory or fill level** for strategic reserves.
- **Any risk score** on chokepoints — that belongs to a dynamic layer.

---

## 6. Manual actions required

| # | Action | Why it needs a human |
| --- | --- | --- |
| M1 | Obtain port-wise **POL (Crude)** traffic — likely *Basic Port Statistics of India* or an IPA request — to resolve L1 | The monthly MoPNG-PS&W reports give commodity totals nationally but not per port |
| M2 | Source an authoritative **Urals / ESPO assay** (L2) | No free official assay was locatable; may need a paid or negotiated source |
| M3 | Decide the **Dubai/Oman price source** (L3) | Likely commercial (Platts/Argus) — a licensing decision, not a technical one |
| M4 | Confirm **which Russian and US routings** to model (L4) | An analytical judgement about what the platform should represent |
| M5 | Re-source **Suez / SUMED / Malacca / Turkish Straits** flows (L6, L7) | EIA's current figures are inside chart images; may need the EIA API or a data request |
| M6 | Geolocate **SPR facilities** from environmental clearance documents (L9) | Requires reading CRZ/EC filings on environmentclearance.nic.in |
| M7 | Decide whether **berth-level coordinates** are needed (L10) | Scope decision affecting how much geospatial work Phase 2 carries |
| M8 | Review and **commit** this work | Nothing has been committed or pushed, per instruction |

---

## 7. Recommended Phase 2 starting point

**Start by making the network connect, not by making it bigger.**

The reference layer currently describes entities well but their *linkages*
weakly. Concretely, in priority order:

1. **Close L1 (port crude handling) first.** It is the single cheapest fix with
   the largest effect: it converts 10 `unknown` values into facts and makes the
   port layer usable as a network entry point. Everything downstream —
   corridors, rerouting, exposure analysis — depends on knowing which ports can
   actually receive crude.

2. **Build the missing link table: refinery ↔ port ↔ pipeline.** Phase 1 has
   refineries and ports as separate node sets with almost no edges between them
   (`refinery_connected` is `yes` for only two ports). Without this table the
   network is two disconnected halves and no rerouting question can be answered.
   This is the natural next *dataset*, and it needs the same provenance
   discipline applied here.

3. **Then resolve the corridors** (L4) and add distances/transit times as an
   explicitly *computed* layer — kept separate from the sourced reference layer,
   with its own provenance describing the method, exactly as `routes.csv` does
   now.

4. **Only then** add the dynamic layer: chokepoint risk, live prices,
   availability. Key it by `chokepoint_id`, `price_series_id` and
   `supplier_id` so it joins cleanly and the reference layer stays static and
   auditable.

**Suggested first deliverable for Phase 2:**
`data/reference/network_links.csv` — sourced edges between refineries, ports,
reserves and pipelines, with a `validate_network_links.py` enforcing that both
endpoints resolve and that no edge is inferred from geographic proximity.

### One principle worth carrying forward

The validators earned their cost in this phase by catching an inference dressed
as a fact (Cochin Port). Phase 2 will face far more pressure to infer, because
network edges are much easier to guess than entity attributes. **Keep the rule
that a claim needs a quotable source, and keep enforcing it in code rather than
in review.**
