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
**Rows:** 32 · **Validator:** `validate_source_registry.py`

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

---

## 11. `pipelines.csv` — crude pipeline master

**Purpose:** the pipeline nodes needed to express refinery ↔ port connectivity
as edges. Deliberately minimal — this is not a pipeline database.
**Rows:** 5 · **Validator:** `validate_network_links.py`
**Phase:** added in Phase 2, step 1.

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `pipeline_id` | text | yes | `PL001`… |
| `pipeline_name` | text | yes | Unique; the operator's own name for the line |
| `operator` | text | yes | As published by the operator |
| `product` | text | yes | `crude oil` throughout — this layer carries no product lines |
| `origin_name`, `destination_name` | text | yes | Plain place names. **Not** foreign keys — a pipeline terminus is not automatically a port or refinery record |
| `length_km` | decimal | yes | As published |
| `capacity_mmtpa` | decimal | **no** | NULL where the operator publishes only a design sizing |
| `status` | text | yes | `operational` \| `under_construction` \| `approved_not_commissioned` \| `suspended` \| `decommissioned` \| `unknown` |
| `commissioned_date` | date | no | Reduced precision (`YYYY`, `YYYY-MM`) allowed |
| `notes` | text | yes | Must open `Evidence: ` and contain `Establishes: ` — enforced |

**Caveats:**

- `origin_name` / `destination_name` are **descriptive, not relational**. Where
  a terminus could not be resolved to a specific reference record it is left as
  a place name and **no edge is created**. Two of five pipelines (PL001, PL005)
  have no sourced marine intake for exactly this reason. Both were
  re-investigated in Phase 2 step 2 and again in step 4, and both are scored
  `PARTIALLY RESOLVED`: their marine intake's operational relationship is
  established, but the specific port record it corresponds to is not — the
  `notes` on each row record exactly what is and is not established, and
  what step 4 additionally attempted and could not retrieve.
- **PL005 carries two published lengths**: 935 km (BPCL's commissioning
  announcement, stored in `length_km`) and 943 km (BORL's own MoEFCC filing,
  preserved in `notes`). Neither was averaged.
- PL004 has a **NULL `capacity_mmtpa`**: its operator publishes only
  "Sized up to 18 MMT", a design sizing, which is not an installed capacity.

---

## 12. `network_links.csv` — refinery / port / pipeline / reserve edges

**Purpose:** the first edge layer of the network. Every row is one
source-backed physical or operational relationship between two reference
records.
**Rows:** 23 · **Validator:** `validate_network_links.py`
**Phase:** added in Phase 2, step 1; extended in Phase 2, step 2; extended in
Phase 3, step 1 (Jamnagar/Sikka edge `NL022`); extended in Phase 3, step 2
(Jamnagar SEZ/Sikka edge `NL023`).

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `link_id` | text | yes | `NL001`… |
| `from_node_type`, `to_node_type` | text | yes | `refinery` \| `port` \| `pipeline` \| `reserve` |
| `from_node_id`, `to_node_id` | text | yes | FK → `refineries.refinery_id`, `ports.port_id`, `pipelines.pipeline_id`, `strategic_reserves.reserve_id` |
| `from_node_name`, `to_node_name` | text | yes | **Must equal the reference record's canonical name exactly.** Enforced |
| `link_type` | text | yes | `port_to_refinery` \| `refinery_to_port` \| `port_to_pipeline` \| `pipeline_to_port` \| `pipeline_to_refinery` \| `refinery_to_pipeline` \| `reserve_to_refinery` \| `reserve_to_port` \| `reserve_to_pipeline` \| `port_to_reserve` \| `pipeline_to_reserve`. **Must agree with the two endpoint types** |
| `operator` | text | yes | Operator of the link itself |
| `status` | text | yes | Same controlled list as `pipelines.status` |
| `notes` | text | yes | Must open `Evidence: `, be ≥ 120 characters, and contain `Establishes: ` — enforced |

**What an edge does and does not assert:**

- It asserts that a **sourced physical or operational connection exists**.
- It asserts **nothing** about volume, throughput, current utilisation,
  direction of flow at any moment, or ownership of the shared asset.
- A reserve edge carries **no inventory or fill-level claim** — the Phase 1 rule
  that strategic reserve rows are capacity-only is unchanged.

**Caveats:**

- **No edge is created from geography.** An endpoint is matched by company and
  published record name, never by map position; `validate_network_links.py`
  rejects rows containing inference wording (`proximity`, `nearby`,
  `assumed`, `presumably`, …).
- **NL011 / NL012** share a caveat: SPM ownership at Paradip is not resolved
  between Paradip Port Authority and IndianOil. Both edges assert the
  operational connection only.
- **NL014** covers the **0.3 MMT commercial compartment only** at
  Visakhapatnam, not the strategic volume.
- **NL016** (Padur → MRPL) is **indirect**, running through an Intermediate
  Valve Station that is not modelled as a node. Transit and capacity modelling
  must account for that.
- **NL017** (Mumbai Port → HPCL Mumbai) covers **imported crude only**. The same
  source records indigenous Mumbai High crude arriving from an ONGC offshore
  terminal, which is not a Mumbai Port facility and is given no edge.
- **NL018** (Mumbai Port → BPCL Mumbai) rests on the **port side only**: the
  port authority names BPCL as a company whose crude requirement it serves, and
  no BPCL document naming a Mumbai Port berth was located.
- **NL019** (Visakhapatnam Port → HPCL Visakh) asserts the crude supply
  relationship, **not ownership of any SPM** — the refinery's own source states
  the VLCC SPM was constructed by the refinery, while the OSTT was commissioned
  by the port.
- **NL020** (Chennai Port → CPCL Manali) exists as a direct port-to-refinery
  edge because the crude line between them has **no published length**, and
  `pipelines.csv` requires `length_km`. Note that `ports.csv` still records
  `crude_handling = unknown` for PORT009: this edge does not change that Phase 1
  value, because the evidence is refinery-side, not port-authority-side.
- **NL021** (Vadinar Offshore Oil Terminal → Nayara Vadinar) carries a
  **jurisdictional conflict** in-row: the operator's filing places the terminal
  under Deendayal Port conservancy, while PORT002's Phase 1 note places private
  Vadinar crude facilities under Gujarat Maritime Board. Unreconciled; PORT002
  was not edited.
- The absence of an edge is **not** evidence that no connection exists. See the
  open evidence gaps in [`data_sources.md`](data_sources.md#network-edge-evidence-gaps).

---

## REFERENCE DATA vs PROCESSED DATA

Every dataset described above, in `data/reference/`, is **REFERENCE DATA**:
a source-backed fact, traceable to a publication in `source_registry.csv`.
Nothing in `data/reference/` is computed, estimated or modelled — the one
documented exception is `routes.csv`/`route_nodes.csv`, whose corridor
*existence* is analyst-modelled but whose node identities are still sourced,
and which is required to carry `NULL` distance/transit values for exactly
this reason.

Starting Phase 2 step 5, `data/processed/` holds **PROCESSED DATA**: values
*computed* from reference-layer facts (principally coordinates), never
observed or published by any third party. A processed value is not "less
true" than a reference value, but it answers a different question — a
reference row says "a source states X"; a processed row says "given sourced
inputs A and B, a stated method computes Y." The two must never be mixed in
one file, and a computed value must never be written back into
`data/reference/` (`validate_computed_routes.py` §E enforces this for
`routes.csv` on every run).

## 13. `data/processed/computed_routes.csv` — computed route distances

**Purpose:** a derived layer estimating plausible distances for the corridors
already asserted (not observed) in `routes.csv`, kept strictly separate from
that reference file.
**Rows:** 9 (8 routes; `RT004` has two branch variants) · **Validator:**
`validate_computed_routes.py`
**Phase:** added in Phase 2, step 5.

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `route_id` | text | yes | FK → `routes.route_id` |
| `route_variant` | text | no | Blank, or a branch label (`via_suez` / `via_sumed`) for `RT004`'s `SUEZ_OR_SUMED` alternative in `route_nodes.csv` |
| `origin_node` | text | no | FK → `suppliers.supplier_id` where the route has one; blank for `RT004`, which has no single origin |
| `destination_node` | text | yes | FK → `ports.port_id` |
| `distance_km` | decimal | no | **Geodesic (great-circle) distance, NOT a sailing distance.** NULL where fewer than two nodes in the route's chain have a sourced coordinate |
| `distance_coverage` | text | yes | `full` \| `partial_last_leg_only` \| `none` — every route so far is `partial_last_leg_only` or `none`; **no route in this dataset has full coordinate coverage from origin to destination**, because `suppliers.csv` and every named export terminal carry no coordinate |
| `estimated_transit_days` | decimal | no | **NULL on every row.** No authoritative vessel-speed or transit-time assumption exists anywhere in this project; inventing one would fabricate a figure indistinguishable from a real one downstream, which is exactly the Phase 1 rule this row extends |
| `transit_time_method` | text | no | NULL wherever `estimated_transit_days` is NULL — there is no method to state for a value that was deliberately not computed |
| `distance_method` | text | yes | `geodesic_haversine_partial_chain` (sum of `route_segments.csv` rows) or `not_computable` |
| `computed_at` | date | yes | Date this derived value was computed (distinct from any source's `retrieved_at`) |
| `notes` | text | yes | States exactly which leg of the route the distance does and does not cover |

**Caveats:**

- **No route has a computable full origin-to-destination distance.**
  `suppliers.csv` (every origin country) and every plain-text export
  terminal/sea-area node in `route_nodes.csv` carry no coordinate anywhere in
  this project. Only chokepoints and ports have sourced coordinates, so a
  distance can only ever be computed for the segment **from the last
  coordinate-resolvable node before the destination**, never the whole
  corridor. `distance_coverage = partial_last_leg_only` says this explicitly
  on every non-NULL row, and it must not be read as "distance from origin."
- **`RT002`, `RT005`, `RT008` have `distance_km = NULL`** — each has only one
  coordinate-resolvable node (the destination port) anywhere in its chain, so
  no segment at all can be formed.
- **A geodesic distance is a straight line through the earth's surface
  ellipsoid model, not a navigational route.** It ignores coastlines, canal
  transit, traffic separation schemes and the actual shipping lane (for
  example `CP006` Cape of Good Hope's coordinate is the OSM headland
  landmark, not the sea lane that passes further south). It must never be
  presented as a sailing distance.
- **`RT004`'s two variants are not comparable to each other.** `via_suez`
  includes a computed Suez-to-Bab-el-Mandeb leg; `via_sumed` does not, because
  `CP004` (the SUMED pipeline) has no coordinate in `chokepoints.csv` — it is
  a linear feature, not a point. The `via_sumed` figure is therefore *smaller*
  for a structural reason (a whole leg is simply missing), not because that
  routing is shorter.

## 14. `data/processed/route_segments.csv` — computed route sub-legs

**Purpose:** the individual coordinate-resolvable geodesic segments that
`computed_routes.csv`'s `distance_km` sums. Exists because several routes
need more than one resolvable leg (for example `RT004 via_suez`), and because
showing the segment breakdown lets a reader see exactly which physical gap in
the corridor was skipped, rather than only a single opaque total.
**Rows:** 7 · **Validator:** `validate_computed_routes.py`
**Phase:** added in Phase 2, step 5.

| Column | Type | Required | Allowed values / notes |
| --- | --- | --- | --- |
| `segment_id` | text | yes | `RS001`… |
| `route_id` | text | yes | FK → `routes.route_id` |
| `route_variant` | text | no | Matches the parent row in `computed_routes.csv` |
| `sequence_no` | integer | yes | Position of this segment within its route/variant |
| `from_node_type` / `to_node_type` | text | yes | `chokepoint` \| `port` |
| `from_node_id` / `to_node_id` | text | yes | FK → `chokepoints.chokepoint_id` or `ports.port_id` |
| `from_node_name` / `to_node_name` | text | yes | Descriptive, must match the reference record |
| `distance_km` | decimal | yes | Great-circle distance between the two coordinates, haversine formula, `R = 6371.0088 km` |
| `distance_method` | text | yes | `geodesic_haversine_r6371.0088km` on every row currently populated |
| `computed_at` | date | yes | — |
| `notes` | text | yes | States which coordinates were used and which intervening named nodes (with no sourced coordinate) were skipped |

**Caveats:**

- **Every segment skips over intermediate named nodes that have no sourced
  coordinate** (plain-text sea areas like "Persian Gulf" or "Arabian Sea",
  and named-but-unlocated export terminals like "Yanbu" or "Fujairah"). The
  segment is a straight line between the two nearest coordinate-bearing
  points in the route's own sequence, not a claim that nothing physical lies
  between them.
- **`RS006`/`RS007` are numerically identical** (`CP006` Cape of Good Hope to
  `PORT006` New Mangalore Port) because `RT006` (Nigeria) and `RT007`
  (Brazil) share the same rounding-the-Cape chokepoint and destination port
  in `route_nodes.csv`. Neither figure represents an origin-to-India
  distance.
- `validate_computed_routes.py` independently **recomputes every
  `geodesic_haversine_r6371.0088km` segment from `ports.csv` /
  `chokepoints.csv` coordinates on every run** and fails if the stored value
  drifts from the recomputation by more than 0.5 km — a computed dataset that
  cannot be reproduced from what it claims to be computed from is worse than
  an unsourced fact, because it looks auditable and is not.
