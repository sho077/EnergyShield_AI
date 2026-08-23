# Data Dictionary

Column-level documentation for every dataset in `data/reference/`.

## Conventions that apply to every dataset

| Convention | Rule |
| --- | --- |
| NULL | An **empty field**. Always means "no authoritative value was available", never zero, never "no". The reason is recorded in that row's `notes`. |
| Dates | ISO-8601 `YYYY-MM-DD`. Reduced precision (`YYYY-MM`, `YYYY`) only where a column is explicitly documented as allowing it. |
| Units | Stated in the column name (`capacity_mmt`, `api_gravity_deg`, `baseline_oil_flow_mbd`). Never converted or reinterpreted. |
| `source` | Human-readable description of the publication the row's facts came from. |
| `source_url` | URL of that publication. |
| `report_date` | Date the source data is effective for. Where a page carries no publication date it equals `retrieved_at`, and the row's `notes` say so. |
| `retrieved_at` | Date this project collected the row. |
| `notes` | Free text. Carries verbatim source quotes, caveats, and the reason for every NULL. **Required on all Phase 1 datasets.** |
| Controlled values | Lower-case `snake_case`. `yes` / `no` / `unknown` triples never use blank for "unknown". |
| Encoding | UTF-8, `\n`-terminated, RFC 4180 quoting. |

**`unknown` is not `no`.** Throughout this layer, `unknown` means no
authoritative source was located. It must never be read as a finding of absence.

---

## 1. `refineries.csv` — refinery master

**Purpose:** supply-side nodes of the network — India's operating refineries and
their installed capacity.
**Rows:** 24 · **Validator:** `validate_refineries.py`
**Status:** pre-existing and independently validated. **Not modified in Phase 1.**

| Column | Type | Unit | Required | Allowed values / notes |
| --- | --- | --- | --- | --- |
| `refinery_id` | text | — | yes | `R001`…`R024`, unique, gapless |
| `refinery_name` | text | — | yes | As published by PPAC, including footnote markers |
| `company` | text | — | yes | As published (mixed capitalisation preserved) |
| `state` | text | — | yes | As published — *not* strictly state-level |
| `capacity_mmtpa` | decimal | MMTPA | yes | ≥ 0. **Installed** capacity, not throughput |
| `source`, `source_url`, `report_date`, `retrieved_at` | — | — | yes | Standard provenance |

**Caveats** (carried forward unchanged from the original documentation):

- `state` reflects PPAC's own labelling; the two CPCL entries are listed under
  `CHENNAI` rather than Tamil Nadu.
- `CPCL, Cauvery Basin` is recorded at `0.0` MMTPA (not in operation). It is a
  valid record and its **absence is a critical failure** — zero-capacity rows
  are retained, never deleted.
- Capacity is *installed* capacity. It must not be used as a proxy for actual
  processed volume.
- Total installed capacity = **267.116 MMTPA**, asserted exactly by the validator.

---

## 2. `strategic_reserves.csv` — strategic petroleum reserves

**Purpose:** ISPRL crude storage facilities as buffer nodes.
**Rows:** 5 (3 Phase I commissioned, 2 Phase II approved) · **Validator:** `validate_strategic_reserves.py`

| Column | Type | Unit | Required | Allowed values / notes |
| --- | --- | --- | --- | --- |
| `reserve_id` | text | — | yes | `SPR001`… |
| `reserve_name` | text | — | yes | Unique |
| `operator` | text | — | yes | ISPRL |
| `phase` | text | — | yes | `Phase I` \| `Phase II` |
| `operational_status` | text | — | yes | `commissioned` \| `approved_not_commissioned` \| `under_construction` |
| `location`, `state_or_region` | text | — | yes | As published |
| `latitude`, `longitude` | decimal | degrees | **no** | NULL throughout — see caveats |
| `capacity_mmt` | decimal | MMT | yes | ≥ 0. **Storage capacity, never inventory** |
| `facility_type` | text | — | yes | `underground rock cavern` |
| `connected_refinery_or_refineries` | text | — | no | Only where officially stated |
| `coastal_access`, `pipeline_access` | text | — | yes | `yes` \| `no` \| `unknown` |
| `commissioned_date` | date | — | no | `YYYY-MM-DD` or `YYYY-MM` (reduced precision allowed) |

**Caveats:**

- **Capacity is not inventory.** The validator rejects any column named for
  inventory, fill level, utilisation or days-of-cover, and requires every
  commissioned row to state this in `notes`. No fill level is recorded, and
  days-of-cover must not be derived from storage capacity alone.
- **Phase II rows are not built.** SPR004 and SPR005 are approved design
  capacity. They must not be added to national available storage.
- **Coordinates are NULL for all five rows.** ISPRL does not publish facility
  coordinates and an Overpass/OSM query returned no ISPRL feature.
- **Source conflict** on the Phase I total (5.03 vs 5.33 MMT) — see
  [`data_sources.md`](data_sources.md).

---

## 3. `ports.csv` — Indian crude/petroleum ports

**Purpose:** maritime entry points for crude into the Indian network.
**Rows:** 18 · **Validator:** `validate_ports.py`

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `port_id` | text | yes | `PORT001`… |
| `port_name` | text | yes | Unique, canonical |
| `port_authority_or_operator` | text | yes | — |
| `parent_port_id` | text | no | FK → `ports.port_id`, for constituent terminals/docks |
| `city`, `state`, `country` | text | yes | `country` = `India` |
| `latitude`, `longitude` | decimal | no | Within India's bounding box |
| `coordinate_precision` | text | no | `facility` \| `berth` \| `locality` — **all current rows are `locality`** |
| `coordinate_source`, `coordinate_source_url` | text | no | Separate provenance for the geolocation |
| `port_class` | text | yes | `major_port` \| `major_port_constituent_terminal` \| `major_port_constituent_dock` \| `major_port_notified_not_operational` \| `non_major_port` |
| `port_role` | text | yes | Descriptive |
| `crude_handling` | text | yes | `yes` \| `no` \| `unknown` |
| `refinery_connected`, `pipeline_connected`, `storage_connected` | text | yes | `yes` \| `no` \| `unknown` |

**Caveats:**

- **No handling capacity is recorded.** None was sourced per port; the validator
  rejects any capacity/throughput/berth-count column outright.
- **`crude_handling = yes` requires a verbatim quote** in `notes`. Enforced.
  During construction the validator rejected an inference for Cochin Port
  (crude presumed from the presence of an SPM); it was corrected to `unknown`.
- **10 of 18 ports are `unknown`** for crude handling. That is a sourcing gap,
  not a finding of "no".
- **Constituent rows must never be summed with their parent.** PORT002 (Vadinar)
  sits inside PORT001; PORT014 (Haldia) sits inside PORT013. Enforced.
- **Coordinates are locality centroids, not berths.** Unusable for berth-level
  modelling.
- PORT017 and PORT018 are **notified but not operational**.

---

## 4. `suppliers.csv` — supplier / origin country master

**Purpose:** reference list of candidate crude origin countries.
**Rows:** 10 · **Validator:** `validate_suppliers.py`

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `supplier_id` | text | yes | `SUP001`… |
| `country` | text | yes | **UN M49 name, verbatim** ("Russian Federation", not "Russia") |
| `iso_alpha3` | text | yes | Three upper-case letters |
| `un_m49_code` | text | yes | Three digits, **leading zeros preserved — store as text** |
| `region`, `subregion` | text | yes | UN M49 groupings |
| `major_export_ports` | text | no | Only where officially named |
| `major_crude_grades` | text | no | `;`-separated FK → `crude_grades.crude_grade_id` |
| `india_supply_relevance` | text | yes | **`reference_candidate_origin` only** |
| `sanctions_reference_status` | text | yes | `ofac_country_program_listed` \| `no_ofac_country_program_listed` \| `not_assessed` |

**Caveats:**

- **This is not a ranking.** `india_supply_relevance` holds one neutral value for
  every country, and the validator fails if any other value appears or if any
  column implying volume, share, price or rank is added. Row order carries no
  meaning.
- **`no_ofac_country_program_listed` does not mean "no sanctions exposure."** It
  means only that no *country-based* OFAC program bears that country's name.
  Thematic programs reach any country — see `sanctions.csv` record SAN008.
- No export ports or crude grades were sourced for Kuwait, Nigeria, Angola,
  Brazil or Canada.

---

## 5. `crude_grades.csv` — crude grade master

**Purpose:** crude properties for future refinery-compatibility modelling.
**Rows:** 14 · **Validator:** `validate_crude_grades.py`

| Column | Type | Unit | Required | Allowed values / notes |
| --- | --- | --- | --- | --- |
| `crude_grade_id` | text | — | yes | `CG001`… |
| `crude_grade` | text | — | yes | Unique |
| `country` | text | — | yes | May list two (Brent) |
| `producer` | text | — | no | NULL where the source names none |
| `api_gravity_deg` | decimal | °API | no | Point value, 0–60 |
| `api_gravity_range_deg` | text | °API | no | Published range, **verbatim** |
| `sulfur_pct` | decimal | % mass | no | Point value, 0–10 |
| `sulfur_pct_range` | text | % mass | no | Published range, **verbatim** |
| `classification` | text | — | no | Only where the source states it |

**Caveats:**

- **A row never holds both a point value and a range for the same property.**
  Enforced. Some producers publish bands; collapsing a band to its midpoint
  would manufacture a number no source printed, so bands are stored as text.
- **No synthetic averages exist anywhere in this dataset.**
- **Four rows (CG011–CG014: Brent, WTI, Dubai, Oman) have NULL assay values.**
  EIA states their classification in text but publishes the numbers only inside
  a chart image, which this project does not transcribe.
- **Urals and ESPO are absent entirely.** No authoritative assay was obtained,
  and an identity-only row would have failed the provenance requirement. This is
  the most significant gap in the dataset given Russia's role in Indian supply.
- Every missing assay value must be explained in `notes`. Enforced.

---

## 6. `chokepoints.csv` — global oil chokepoints

**Purpose:** baseline reference for maritime chokepoints.
**Rows:** 7 · **Validator:** `validate_chokepoints.py`

| Column | Type | Unit | Required | Allowed values / notes |
| --- | --- | --- | --- | --- |
| `chokepoint_id` | text | — | yes | `CP001`… |
| `name` | text | — | yes | Unique |
| `type` | text | — | yes | `strait` \| `canal` \| `pipeline` \| `cape` |
| `latitude`, `longitude` | decimal | degrees | no | Full global range |
| `strategic_role` | text | — | yes | Descriptive, sourced |
| `alternative_exists` | text | — | yes | `yes` \| `no` \| `partial` \| `unknown` \| `not_applicable` |
| `baseline_oil_flow_mbd` | decimal | million bbl/day | no | ≥ 0. **Throughput, never capacity** |
| `flow_basis` | text | — | no | What the figure counts |
| `flow_period` | text | — | no | `YYYY` or `YYYY-MM/YYYY-MM` for a partial period |
| `flow_data_origin` | text | — | no | Who *collected* the data |

**Caveats:**

- **There is no `risk_score` here, by design.** The validator rejects any risk,
  threat, severity or current-status column, and any row phrasing a current
  geopolitical condition as a standing fact. Dynamic risk belongs in a later
  layer, keyed to `chokepoint_id`.
- **Flow is not capacity.** SUMED stores throughput (1.6), not its 2.5 mb/d
  capacity; Hormuz stores 20 mb/d transit, not bypass-pipeline capacity.
- **Two periods are partial years** (Jan–Aug 2024) and are not comparable with
  full-year figures. Flagged on every run.
- **Three baselines are from 2016** (Suez, SUMED, Malacca) and are stale.
- **CP007 Turkish Straits has no flow figure at all** — a gap, not a zero.
- CP004 SUMED has NULL coordinates: a pipeline is linear, and a centroid would
  misrepresent it. CP007's coordinate is the Bosporus only; the Dardanelles is
  the same system's second constriction and cannot share one point.

---

## 7. `routes.csv` / `route_nodes.csv` — trade corridors

**Purpose:** ordered network corridors from origin to Indian discharge port.
**Rows:** 8 routes, 42 nodes · **Validator:** `validate_routes.py`

### `routes.csv`

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `route_id` | text | yes | `RT001`… |
| `route_name` | text | yes | Unique |
| `corridor_status` | text | yes | **`modelled` only** |
| `origin_supplier_id` | text | no | FK → `suppliers.supplier_id` |
| `destination_port_id` | text | yes | FK → `ports.port_id`, must have `crude_handling = yes` |
| `estimated_distance_km` | decimal | **no** | **Must be NULL in Phase 1** |
| `estimated_transit_days` | decimal | **no** | **Must be NULL in Phase 1** |
| `chokepoints_involved` | text | no | `;`-separated FK → `chokepoints.chokepoint_id` |
| `corridor_evidence`, `corridor_evidence_url` | text | no | External evidence, where any exists |

### `route_nodes.csv`

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `route_id` | text | yes | FK → `routes.route_id` |
| `sequence_no` | integer | yes | Contiguous `1..N` per route |
| `node_type` | text | yes | `origin_country` \| `export_terminal` \| `chokepoint` \| `sea_area` \| `destination_port` \| `refinery` |
| `node_id_or_name` | text | yes | An ID when `node_reference_table` is set, else a plain name |
| `node_reference_table` | text | no | `suppliers.csv` \| `ports.csv` \| `chokepoints.csv` \| `refineries.csv` |
| `branch_group` | text | no | Marks nodes sharing a `sequence_no` as **alternatives (OR), not sequential legs** |

**Caveats:**

- **Modelled, not observed.** See [`data_sources.md`](data_sources.md#modelled-corridors).
- Distance and transit time are NULL on every route — *to be modelled later*.
- **RT005 (Russia) and RT008 (United States) have no corridor evidence** and no
  determined chokepoint set; each can reach India by materially different paths.
  Phase 2 must split them before either is used in a flow model.
- RT004's two `sequence_no = 2` nodes are the Suez-**or**-SUMED branch.
- Every route must start at an origin/transit node and end at a
  `destination_port`. Enforced.

---

## 8. `sanctions.csv` — sanctions / compliance reference

**Purpose:** **lookup pointers only** to sanctions authorities and program names.
**Rows:** 8 · **Validator:** `validate_sanctions.py`

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `sanction_record_id` | text | yes | `SAN001`… |
| `record_type` | text | yes | `authority` \| `country_program` \| `non_country_program_class` |
| `entity_name` | text | yes | An authority or a program — **never a designated party** |
| `entity_type` | text | yes | `sanctions_authority` \| `sanctions_program` \| `sanctions_program_class` |
| `status` | text | yes | `active` \| `listed_as_active_program` \| `terminated` \| `not_assessed` |
| `is_complete_screening_list` | text | yes | **`no` on every row** |

**Caveats — read before any use:**

- **This is not a screening list and must never be used as one.** Screening must
  be run against the authority's own current list at the time of the
  transaction. The OFAC SDN List, UN Consolidated List and EU Consolidated List
  are deliberately **not** reproduced here: a partial copy of a screening list
  is worse than none, because it looks usable and is silently stale.
- **No designated persons or entities are stored,** and the validator rejects any
  column able to hold a natural-person identifier.
- **No legal interpretation is stored.** Enforced against a phrase list.
- `listed_as_active_program` means only that the program name appeared in the
  authority's published index on `retrieved_at`.
- **SAN008 is a required caveat record** explaining that thematic (non-country)
  programs reach any country. Without it, `suppliers.csv` is misleading.

---

## 9. `energy_prices_reference.csv` — benchmark price series

**Purpose:** define **where** prices come from. **Contains no prices.**
**Rows:** 5 · **Validator:** `validate_energy_prices_reference.py`

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `price_series_id` | text | yes | `PRC001`… |
| `benchmark` | text | yes | Unique |
| `series_name_as_published` | text | no | **Verbatim** publisher heading |
| `unit` | text | yes | `barrel` \| `ratio` |
| `currency` | text | no | Required for monetary series; **must be NULL for `ratio`** |
| `provider` | text | no | NULL where no official series was located |
| `provider_authority_level` | text | no | Registry levels |
| `contains_price_values` | text | yes | **`no` on every row** |

**Caveats:**

- **No price value is stored anywhere in this repository.** The validator rejects
  price-like columns and bare numerics in definition columns. A cached price is
  stale the moment it is written and indistinguishable from a live one.
- **PRC003 Dubai/Oman has no provider.** No free, official, machine-readable
  series was located — the most consequential gap here, since Dubai/Oman is the
  benchmark Saudi Aramco uses for crude sold to Asia.
- PRC004's `currency` is `USD; INR`. The two must never be mixed in one column.
- PPAC delivers its tables via JavaScript, so `frequency` and `series_start`
  could not be read as text and are NULL rather than assumed.

---

## 10. `source_registry.csv` — source registry

**Purpose:** the index making every dataset traceable.
**Rows:** 27 · **Validator:** `validate_source_registry.py`

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `source_id` | text | yes | `SRC001`… |
| `dataset_name` | text | yes | `;`-separated where a source feeds several |
| `dataset_file` | text | yes | Repo-relative path(s); **must exist on disk** |
| `source_name` | text | yes | — |
| `authority_level` | text | yes | `official_india` \| `official_international` \| `authoritative_public` \| `commercial` \| `secondary` |
| `update_frequency` | text | yes | As published, or `not established` |
| `retrieval_method` | text | yes | How the data was obtained |
| `last_checked` | date | yes | — |

**Coverage is enforced in both directions:** every reference dataset on disk must
appear in the registry, every `dataset_file` named must exist, and every
`source_url` used by any reference dataset must be declared here. The registry
does not register itself.
