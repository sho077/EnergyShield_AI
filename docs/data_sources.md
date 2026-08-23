# Data Sources

Every figure in `data/reference/` traces to a source recorded here and in
`data/reference/source_registry.csv`. This document explains the sourcing
*policy*; the registry is the machine-readable index.

## Source hierarchy

| Level | Meaning | Used for |
| --- | --- | --- |
| `official_india` | PPAC, MoPNG, ISPRL, PIB, port authorities, Gujarat Maritime Board, MoEFCC filings, and Government of India PSUs publishing their own assets (IndianOil, BPCL, HPCL, CPCL) | All India-specific facts |
| `official_international` | EIA, UN, OFAC, national oil companies publishing their own product specs | Global chokepoints, crude assays, sanctions programs, benchmarks |
| `authoritative_public` | OpenStreetMap / Nominatim | Coordinates only |
| `commercial` | Private operators publishing their own assets (HMEL) | **Unused in Phase 1.** One source in Phase 2, always corroborated by an official one |
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
data/raw/isprl/   ISPRL CRZ executive summary (PDF), the sole source for
                  the reserve-to-refinery edges NL015 and NL016
data/raw/hpcl/       HPCL "Our Refineries" page, the source for NL017 and NL019
data/raw/cpcl/       CPCL "New Crude Oil Pipeline Project" page, source for NL020
data/raw/vizagport/  Visakhapatnam Port Authority handling facilities page
data/raw/nayara/     Coviva/Nayara SPM brief summary (PDF), source for NL021
data/raw/borl/       BORL Vadinar crude storage pre-feasibility report (PDF)
```

Two Phase 2 step 2 documents are **not** committed because of their size: the
Mumbai Port Trust JD5 EIA executive summary (1.7 MB) and the Mumbai Port
Authority Citizen's Charter (0.8 MB). Both are reachable from their
`source_url` in the registry (SRC034, SRC035).

Large PDFs (the MoPNG-PS&W Annual Report, EIA country analyses) were read during
collection but are **not** committed, to keep the repository small. Each is
reachable from its `source_url` in the registry.

---

## Network edges (Phase 2, step 1)

`network_links.csv` and `pipelines.csv` are **sourced observations**, not
modelling. They sit at the opposite end of the spectrum from `routes.csv`: a
corridor asserts a plausible routing, an edge asserts a connection somebody
published.

### The rule that governs this layer

**A claim needs a quotable source, enforced in code rather than in review.**
Concretely, `validate_network_links.py` fails a row unless:

* both endpoints resolve **by id** against a reference dataset, **and** the
  stored endpoint name matches that record's canonical name character for
  character — so an edge is anchored to a record, never to a place;
* `link_type` agrees with the two endpoint types, so a reversed edge cannot
  read as correct;
* `notes` opens with `Evidence: `, runs to at least 120 characters, and says
  what the source `Establishes: `;
* no field anywhere in the row contains inference wording — `proximity`,
  `nearby`, `adjacent to`, `close to`, `geographically`, `assumed`,
  `presumably`, `probably`, `most likely`, `appears to be`, `we infer`,
  `seems to`. (Plain `near` is permitted because it occurs inside verbatim
  source quotes, as in "Salaya near Vadinar".)

### How endpoints were matched

Every refinery endpoint was matched to `refineries.csv` by **company and
published refinery name** as PPAC prints them — for example the operator's
"Guru Gobind Singh Refinery" to PPAC's `HMEL, GGSR` under HPCL-MITTAL ENERGY
LIMITED in PUNJAB. Every port endpoint was matched by **named operator or
jurisdiction** — for example IndianOil's "Gujarat Adani Port's Single Point
Mooring" to `PORT015`, whose `port_authority_or_operator` is Adani Ports and
Special Economic Zone Limited. No endpoint anywhere was matched by coordinates,
district, or distance.

### Documented source conflicts in this layer

**BORL's crude SPM — Sikka or Vadinar?**
Gujarat Maritime Board's captive-jetty register lists `BORL - SPM  Sikka  Crude
oil`, which is the evidence `ports.csv` records for `PORT016`. BPCL's own
commissioning announcement for the Vadinar–Bina pipeline names **Vadinar** as
the marine end. Both are official Indian sources and they name different
localities. **`PL005` is therefore given no port endpoint at all**, and neither
`PORT016` nor `PORT002` is linked to it.

Phase 2 step 2 sharpened this from an open question into a **characterised
conflict**. BORL's own pre-feasibility report, filed on the Government of India
environmental clearance portal (SRC039), states that BORL operates **exactly one**
SPM, gives its position — "Lat. 22o 33' 44'' N, Long. 69o 45' 38'' E, about 7 km
offshore from the Vadinar coast" — and describes the CALM buoy feeding a Crude
Oil Terminal at Vadinar from which "the crude oil is pumped … through a 943 km
long pipeline to Bina". The GMB register likewise lists exactly one `BORL - SPM`.
One facility, therefore, carried under **two different locality labels by two
official publishers**.

What that changes and what it does not:

* **Established:** the marine intake of `PL005` is BORL's own SPM discharging
  into BORL's own Crude Oil Terminal. That relationship is not in doubt.
* **Not established:** which `ports.csv` record holds that facility. `PORT016`
  is the GMB captive-jetty cluster at Sikka; `PORT002` is the Deendayal Port
  Authority terminal, whose own row explicitly excludes privately operated
  crude facilities. Creating an edge to either would silently adopt one
  publisher's locality label over the other's.
* **Decision:** no port endpoint for `PL005`. The endpoint — not the
  relationship — is what remains unresolved, and `PL005`'s `notes` now say so
  in those terms.

**Vadinar–Bina pipeline length — 935 km vs 943 km.**
BPCL's commissioning announcement gives 935 km; BORL's own filing gives 943 km
for the same line. `pipelines.csv` stores the 935 km commissioning figure in
`length_km` and preserves 943 km in `notes`. Neither was averaged.

**Nayara's Vadinar marine facility — Deendayal conservancy or GMB jurisdiction?**
`PORT002`'s Phase 1 note states that "Separate privately operated crude
facilities also exist at Vadinar under Gujarat Maritime Board jurisdiction; they
are NOT represented by this row". The MoEFCC filing by Coviva Energy Terminals
Limited (SRC038) states instead that "Nayara Energy's Vadinar Oil Terminal
presently operates the Marine facility under conservancy of DPT (Deendayal port
trust) OOT (Offshore Oil Terminal) off Vadinar, Gujarat", and Nayara's terminal
appears in **neither** GMB register — not the captive-jetty list, not the
private-jetty list. The edge `NL021` was created on the strength of the
operator's own filing naming the Deendayal terminal, and the conflict is
recorded in-row. **`PORT002` itself was not edited**: correcting a Phase 1
attribute is a separate decision from adding an edge.

**Paradip SPM ownership.**
Paradip Port Authority lists "3 (three) Single Point Moorings (SPMs)" as port
equipment; IndianOil describes crude receipt "by 3 nos. Single Point Mooring
(SPM)" and a 102 km offshore pipeline from "three Single Point Mooring
systems". The count and location agree; **ownership does not resolve**. `NL011`
and `NL012` assert the operational connection only and say so in-row.

Phase 2 step 2 re-opened this question and **did not close it**. Paradip Port
Authority's scale-of-rates documents and its marine-department notice on the
IOCL SPM are published as PDFs that no longer resolve (HTTP 404), and no other
port-authority or MoPNG document reconciling ownership was readable. Commercial
vessel directories do list the buoys as "IOCL PARADIP SPM II / III", but a
commercial directory is not an acceptable basis for an ownership claim in this
repository and that evidence was **rejected**, not used.

### Network edges added in Phase 2, step 2

Five candidates from the step 1 gap list were closed. Each rests on a document
by the operator of one endpoint or the authority governing the other, never on
map position:

| Edge | What the source establishes | Publisher |
| --- | --- | --- |
| `NL017` `PORT003` → `R010` | HPCL: Mumbai Refinery's imported crude arrives by "marine tankers berthed at Jawahar Dweep jetty" | HPCL (SRC033), corroborated by the Mumbai Port Authority Citizen's Charter (SRC035) |
| `NL018` `PORT003` → `R012` | Mumbai Port Trust: "The crude traffic through MbPT is primarily to cater the requirement of HPCL and BPCL" | MbPT EIA executive summary published by MPCB (SRC034) |
| `NL019` `PORT011` → `R011` | HPCL: Visakh Refinery receives crude from "the Oil Wharf Jetties located in Visakhapatnam Port Trust (VPT)" and the VPT-commissioned OSTT | HPCL (SRC033), corroborated by the port's own handling-facilities register (SRC036) |
| `NL020` `PORT009` → `R015` | CPCL: a 42-inch crude line "increasing Crude transfer from Chennai Port Trust to CPCL", commissioned Dec 2018 | CPCL (SRC037) |
| `NL021` `PORT002` → `R024` | Coviva/Nayara: the Vadinar Oil Terminal marine facility operates "under conservancy of DPT … OOT … off Vadinar" and services "the crude intake … of Nayara Energy Refinery" | MoEFCC filing (SRC038) |

Three of these carry an explicit in-row caveat — `NL018` is evidenced from the
port side only, `NL019` asserts no SPM ownership, `NL021` records an
unreconciled jurisdictional conflict. See the caveat list in
[`data_dictionary.md`](data_dictionary.md).

One deliberate **non-change**: `NL020` does not license flipping
`ports.csv`'s `crude_handling` for `PORT009` from `unknown` to `yes`. The
evidence is refinery-side; the Phase 1 value is a statement about what the port
authority publishes, and it stands until a port-authority source is found.

<a id="network-edge-evidence-gaps"></a>

### Network edge evidence gaps

Candidate edges that were investigated and **deliberately not created**,
because no authoritative source supported them:

| Candidate edge | Why it was not created |
| --- | --- |
| `PL001` (Salaya–Mathura) ← a port | **Re-investigated in step 2 and step 4 — PARTIALLY RESOLVED, still no port endpoint.** IndianOil's own page yields more than step 1 recorded: "Two Single Point Mooring (SPM) systems are operated at Vadinar to unload the crude oil received from tankers …" plus an 18-tank, 1.5 MMT IndianOil crude farm at Vadinar. The line's marine intake **is** at Vadinar under IndianOil operation — that relationship is established. What is still missing is the port record: MoPNG-PS&W counts **three** SBMs at Vadinar under Deendayal Port Authority (`PORT002`), IndianOil counts **two** of its own, and no source reconciles the counts or states that IndianOil's are Deendayal facilities. Step 4 sought the two documents most likely to reconcile this directly — Deendayal Port Authority's own "Off-shore Oil Terminal (OOT) – Vadinar" page and a Tariff Authority for Major Ports order on the same terminal — and could not retrieve either: the DPA page returns the site's own application-error screen on every attempt with no archived snapshot, and the TAMP order's host refused every connection attempt. Both are documented as failed retrievals, not evidence. |
| `PL005` (Vadinar–Bina) ← a port | **Re-investigated in step 2 and step 4 — PARTIALLY RESOLVED, still no port endpoint.** One BORL facility is carried under two official locality labels; see the conflict section above. Step 4 found no document naming the facility under one label together with coordinates, operator and terminal name, and confirmed Gujarat Maritime Board's own site carries no separate "Vadinar" port page (HTTP 404) — its only record of this facility remains the captive-jetty register's Sikka entry already on file. |
| `PORT003` Mumbai Port → `R012` — *refinery-side evidence* | The **edge now exists** (`NL018`) on port-authority evidence. What remains missing is any BPCL document naming a Mumbai Port berth: BPCL's refinery pages describe no crude receipt infrastructure, and its JD5 commissioning statements appear only on social and locator channels this repository does not accept as sources. |
| `PORT001` Deendayal Port / `PORT016` Sikka → any refinery | **Closed for `PORT016` in Phase 3 steps 1-2**: `PORT016` → `R022` (`NL022`, step 1) and `PORT016` → `R023` (`NL023`, step 2) both now exist on RIL's own EC compliance filing — see [Phase 3, step 1](#phase-3-step-1-jamnagar-network-connectivity) and [Phase 3, step 2](#phase-3-step-2-r023-jamnagar-sez-crude-receipt-path) below. `PORT001` (the parent Deendayal Port record, as distinct from its `PORT016` Sikka constituent terminal) remains open. The BORL captive-jetty entry's own locality question (Sikka vs Vadinar, `PL005`) is unaffected and still contested. |
| `PL002` → `R008` Bongaigaon / `R002` Guwahati | The operator's own sentence says Bongaigaon is reached through **Oil India Limited's** pipeline and Guwahati **by rail rake** — neither is PL002. |
| `PORT006` New Mangalore Port → `SPR002` | ISPRL's filing places the booster station in the "Mangalore Port Area" but does not state that the SPM or the cavern is a New Mangalore Port facility. |
| Paradip SPM ownership | Unresolved between Paradip Port Authority and IndianOil; step 2 found no readable reconciling document. `NL011` / `NL012` continue to assert the operational connection only. |
| `SPR004` Chandikhol, `SPR005` Padur II | Approved, not commissioned. No connection can be operational. |
| Paradip–Numaligarh Crude Pipeline (PNCPL) | Under construction, not commissioned, and no official operator page describing it was readable. Out of scope for a layer of operational relationships. |
| JNPT (`PORT004`) crude handling | A BPCL tender document describes a liquid-cargo jetty inside Jawaharlal Nehru Port, owned jointly with IOCL, handling "Crude oils" among other cargoes. It names **no refinery**, so no edge follows. Recorded here as a lead for a future `ports.csv` review, not as a finding. **Phase 2 step 3 checked this lead and still could not act on it**: no `source_url`, report date, or archived copy of the tender exists anywhere in this repository or the source registry, so it cannot meet this project's provenance bar (`source` + `source_url` + date + verbatim quote). `PORT004` remains `unknown` on all four attributes pending a properly sourced document. |

### `ports.csv` attribute review (Phase 2, step 3)

Step 3 reviewed `crude_handling`, `refinery_connected`, `pipeline_connected` and
`storage_connected` on the four ports touched by step 2's new evidence, using
only sources already established as sufficient for `network_links.csv` (never
inferring one attribute from evidence for a different one):

* **`PORT009` Chennai Port** — CPCL's own page (SRC037, the same source behind
  `NL020`) describes a dedicated 42-inch crude line "increasing Crude transfer
  from Chennai Port Trust to CPCL." This is refinery-side evidence naming both
  ends of a physical connection, so `refinery_connected` and
  `pipeline_connected` move from `unknown` to `yes`. `crude_handling` is
  **deliberately left `unknown`**: the CPCL page is CPCL describing its own
  inbound asset, not Chennai Port Authority declaring the port handles crude —
  the same distinction the step 2 "deliberate non-change" note above already
  draws, and step 3 does not overturn it.
* **`PORT003` Mumbai Port** — Mumbai Port Trust's own EIA/EMP executive summary
  (SRC034) states "the crude traffic through MbPT is primarily to cater the
  requirement of HPCL and BPCL," and the Mumbai Port Authority's own Citizen's
  Charter (SRC035) states the Jawahar Dweep berths "are connected to the
  refineries on shore at Mahul through submarine pipelines," corroborated by
  HPCL's "pumped to Refinery Crude storage tanks" (SRC033). `refinery_connected`
  and `pipeline_connected` move from `unknown` to `yes` on this port-authority
  and refinery-operator evidence (the same sources behind `NL017`/`NL018`).
  `crude_handling` was already `yes` from Phase 1 and is unchanged.
  `storage_connected` stays `unknown` — the crude storage named in these
  sources is at the refinery, not asserted to be a port facility.
* **`PORT011` Visakhapatnam Port** — Visakhapatnam Port Authority's own
  Handling Facilities page (SRC036) states its Offshore Tanker Terminal
  discharges "direct discharge from berth to the refinery tanks @ 5500 tonnes
  per hour through pipe lines" — the port authority's own statement of a
  pipeline to a named-in-substance refinery, corroborated by HPCL naming Visakh
  Refinery as the recipient (SRC033, the same source pair behind `NL019`).
  `refinery_connected` and `pipeline_connected` move from `unknown` to `yes`.
  `crude_handling` was already `yes` from Phase 1 and is unchanged.
  `storage_connected` stays `unknown` — no source describes port-side crude
  storage.
* **`PORT004` JNPT** — no change. See the BPCL tender row above: the lead is
  unsourced by this project's own standard and cannot support a change.

No other port was touched. `network_links.csv`, `pipelines.csv` and
`refineries.csv` are unaffected by this review.

### Targeted marine-intake evidence resolution (Phase 2, step 4)

Step 4 was scoped narrowly to the two remaining pipeline marine-intake gaps —
`PL001` and `PL005` — and to nothing else. Both were re-investigated against
Deendayal Port Authority, TAMP, IndianOil, Gujarat Maritime Board, BORL/BPCL
and MoEFCC sources, in addition to everything already on file.

Neither gap could be closed to `RESOLVED`. Two candidate documents were
identified that could plausibly have reconciled each one directly, and both
proved unreachable:

* Deendayal Port Authority's own "Off-shore Oil Terminal (OOT) – Vadinar"
  page returns the site's own client-side application-error screen
  ("Something went wrong … redirected to the home page") on every retrieval
  attempt, and carries no Wayback Machine snapshot. Per this project's source
  rule, a search-engine summary of that page's content is not treated as
  evidence — only the page itself would be, and it could not be retrieved.
* A Tariff Authority for Major Ports order concerning the Vadinar Off-Shore
  Oil Terminal could not be retrieved at all: the host refused or timed out
  on every connection attempt, direct and proxied.

Both failed retrievals are recorded in `pipelines.csv`, not used as evidence.
No new source was successfully retrieved for either pipeline, so no row was
added to `source_registry.csv` and no edge was added to `network_links.csv`.

Both pipelines are formally scored `PARTIALLY RESOLVED`:

* **`PL001`** — the marine intake's location and operator (Vadinar,
  IndianOil, two SPM systems) are established. The specific port record
  those SPM systems correspond to is not, because no source reconciles
  IndianOil's count of two with MoPNG-PS&W's count of three Single Buoy
  Moorings at Vadinar under `PORT002`.
* **`PL005`** — the operational relationship (BORL's single SPM feeding its
  Bina refinery through the Vadinar-named Crude Oil Terminal) is
  established. The specific port record for that terminal is not, because
  Gujarat Maritime Board's captive-jetty register and BORL/BPCL's own
  filings continue to name the same physical facility under two different
  localities (Sikka and Vadinar) with no reconciling document found.

Neither pipeline's endpoint was guessed from locality wording or coordinate
proximity, consistent with the rule already in force for this layer.

---

## Network connectivity finalisation and the computed route layer (Phase 2, step 5)

Step 5 did not reopen `PL001`/`PL005` — no genuinely new evidence for either
was found or sought, per the standing instruction — and added no new edge to
`network_links.csv`. It did two things instead:

1. **Analysed the existing graph's connectivity** without changing it. See
   [`docs/network_connectivity_report.md`](network_connectivity_report.md) for
   node/edge counts, connected components, and — critically — which of the 23
   isolated nodes are a documented evidence gap versus a correct reflection of
   an unbuilt or excluded facility (`PORT017`/`PORT018` not operational,
   `SPR004`/`SPR005` not commissioned, `R016` zero-capacity). **No edge was
   added to reduce the isolated-node count**; that would be exactly the kind
   of inference this project's validators exist to reject.
2. **Introduced `data/processed/`, a computed layer, strictly separate from
   `data/reference/`.** `computed_routes.csv` and `route_segments.csv` compute
   *geodesic* (great-circle) distances for the corridors in `routes.csv`,
   using coordinates already present in `ports.csv` and `chokepoints.csv`.
   See `docs/data_dictionary.md` §§13–14 for the full column documentation.

### Why no route has a full, origin-to-destination computed distance

`routes.csv`'s origin side is a `suppliers.csv` country or a named export
terminal (Yanbu, Fujairah). **Neither `suppliers.csv` nor any export terminal
name carries a sourced coordinate anywhere in this project** — Phase 1
explicitly did not collect them (see `docs/phase1_report.md` L9/L10 for the
equivalent gap on strategic reserves and port precision). Only
`ports.csv` (locality centroids) and most rows of `chokepoints.csv` have
coordinates. The computed layer is therefore honest about a hard limit: it
can only ever price the **last leg** of a corridor — from whichever
chokepoint or port is nearest the Indian coast in the route's own node
sequence, to the destination port — never the full corridor. Every non-NULL
row in `computed_routes.csv` is tagged `distance_coverage =
partial_last_leg_only` for exactly this reason, and three routes (`RT002`,
`RT005`, `RT008`) have **no** computable segment at all, because their chain
contains only one coordinate-bearing node.

### Geodesic, not sailing, distance

Every computed distance is a great-circle (haversine, spherical Earth,
`R = 6371.0088 km`) distance between two points. This is deliberately **not**
a maritime routing distance: it does not follow a shipping lane, avoid land,
account for a canal transit, or account for the fact that some source
coordinates are locality centroids or headland landmarks rather than the
lane itself (`ports.csv`'s and `chokepoints.csv`'s own caveats already flag
this). No source in this repository publishes an authoritative maritime
routing distance for any of these legs, so none is claimed. A future
navigational-routing source, if one is obtained, must be recorded as a
**separate, better-sourced** `distance_method`, never substituted silently
into the existing geodesic rows.

### No vessel-speed or transit-time assumption

`estimated_transit_days` is NULL on every row of `computed_routes.csv`, for
the same reason `routes.csv` has always kept it NULL: no authoritative
vessel-speed figure has been obtained or assumed. Should a future phase adopt
one (for example, a stated average VLCC speed from a named source), it must
be recorded explicitly as a documented modelling assumption with its own
`transit_time_method` value — never silently divided-in as if it were a fact.

---

## Phase 3, step 1: Jamnagar network connectivity

<a id="phase-3-step-1-jamnagar-network-connectivity"></a>

Step 1 targeted the single largest gap left by Phase 2: `R022` ("RIL,
Jamnagar", 33.0 MMTPA) and `R023` ("RPL (SEZ), Jamnagar", 35.2 MMTPA) carried
zero sourced network edges despite being the two largest refineries in the
country. The two PPAC records are two legally and physically distinguishable
refinery units at the same Jamnagar site — a Domestic Tariff Area (DTA)
refinery and an export-only Special Economic Zone (SEZ) refinery — and this
step deliberately investigated their crude connectivity **separately**,
per the standing instruction not to assume identical connectivity between
them without evidence.

The decisive source was Reliance Industries Limited's own half-yearly
compliance filing to the Ministry of Environment, Forest and Climate Change
(MoEFCC), hosted on RIL's own website (`SRC040`). Unusually for this
repository, this single PDF bundles compliance reporting for several distinct
Jamnagar EC proposals in one document, each under its own "Proposal Name" and
MoEF file number:

| Proposal (as printed in the filing) | MoEF file no. | Entity | Refinery unit |
| --- | --- | --- | --- |
| "18 MMTPA Refinery Complex at Motikhavdi/Sikka, Jamnagar" | J-11011/25/94-IA-II (I) | Reliance Industries Limited | original (DTA) refinery |
| "Jamnagar Refinery Complex of M/s RPL at Motikhavdi ... 18 to 27 MMTPA" | J-11011/25/93-IA-II (I) | Reliance Industries Limited | original (DTA) refinery, expansion |
| "Environmental clearance for expansion and modernization of petrochemical refinery complex ... " (59.7 MMTPA combined) | J.11011/232/2005-IA-II (I) | Reliance Industries Limited | complex-wide (DTA + SEZ) |
| "Petroleum and Petrochemical Complex in Multi products Special Economic Zone" | J-11011/149/2007-IA-II (I) | Reliance Industries Limited | SEZ refinery / JERP |
| "Expansion of production capacity of SEZ refinery from 35.2 MMTPA to 41 MMTPA" | IA/GJ/IND2/79902/2018 | Reliance Industries Limited | SEZ refinery |

Only the first two (DTA) proposals carry environmental-clearance conditions
grouped under "A. SPM and Sub-Sea Pipeline" and "B. CRUDE OIL TERMINAL (COT)",
naming an SPM/SBM system, a submarine and on-shore pipeline, and a Crude Oil
Terminal sited in "the inter-tidal region of Vadinar Sikka". The SEZ-refinery
proposals in the same filing carry no SPM, SBM, COT, or crude-pipeline
condition of their own — only product-jetty, seawater-intake and diffuser
conditions.

### R022 ("RIL, Jamnagar") — RESOLVED (port side)

`NL022` (`PORT016` Sikka → `R022`) was added on this basis, corroborated by
Gujarat Maritime Board's captive-jetty register (`SRC010`, already `PORT016`'s
Phase 1 source), which independently places Reliance-operated SPMs and tanker
berths under GMB jurisdiction at Sikka. `ports.csv`'s `PORT016` row moves
`refinery_connected` and `pipeline_connected` from `unknown` to `yes`.
`storage_connected` stays `unknown`: the Crude Oil Terminal the filing
describes is a refinery-side facility (its own conditions reference a green
belt "around the crude oil terminal site" and "crude oil tanks bottom"
sludge), not storage stated to be held by the port/GMB itself.

No pipelines.csv record was created for the submarine/on-shore pipeline: the
filing states no length for it, consistent with the treatment already given
to CPCL's unmeasured Chennai crude line (`NL020`).

### R023 ("RPL (SEZ), Jamnagar") — PARTIALLY RESOLVED at step 1; RESOLVED at
step 2 (see below)

No SPM, SBM, COT, or crude-pipeline condition was found attached to either
SEZ-refinery proposal in RIL's own filing. A second official filing was
consulted for background — Reliance Jamnagar Infrastructure Limited's
consolidated EIA for the Petroleum and Petrochemicals Complex, submitted to
MoEF in October 2009 (`SRC041`) — which states, in its own section on the
JERP (SEZ) refinery: "The petroleum products from the crude refinery, LOBS
will be accommodated in the existing Refinery and the Marine Tank Farm area",
and separately, on SEZ seawater supply: water is sourced "as in the case of
the existing refinery" through "the existing seawater intake provided at the
marine terminal area". Both sentences describe the SEZ refinery using the
pre-existing (DTA) refinery's Marine Tank Farm and marine terminal rather
than a separate one of its own — but neither sentence names a crude-specific
SPM or pipeline path for the SEZ refinery, only product accommodation and
seawater intake. That falls short of this project's evidence bar for a
`network_links.csv` edge (a source establishing the crude relationship and,
where a pipeline is involved, its endpoint), so **no edge was created for
`R023`** at this step, and `PORT016`'s `refinery_connected = yes` was **not**
read as covering `R023`.

**Step 1 decision: `R022` RESOLVED (port-to-refinery edge, `NL022`); `R023`
PARTIALLY RESOLVED (shared-Marine-Tank-Farm infrastructure indicated, no
crude-specific SPM/pipeline statement found, no edge created).** This was a
narrower finding than "the two refineries share a marine terminal" would be;
it should be read as "the SEZ refinery's own filings describe using the
existing refinery's product/seawater infrastructure" only.

**This finding was revised in Phase 3 step 2** — see
[Phase 3, step 2](#phase-3-step-2-r023-jamnagar-sez-crude-receipt-path)
below — after a Marine/Coastal condition naming crude-handling SPMs was
found within a third proposal in the same compiled filing that step 1 had
not examined for marine/crude conditions.

### What was investigated and not used

* Global Energy Monitor, ShipNext, Delta Group, findaport.com and other
  vessel-tracking / port-directory pages were consulted only to orient the
  search (confirming "Sikka" and "Reliance Jamnagar Marine Terminal" as the
  relevant names); none of them carries a `source_url` + date + verbatim
  quote this project accepts as evidence, and none was used to source a row.
* The RIL filing's own PDF could not be parsed by this project's standard
  web-fetch text extractor (the tool reported a "corrupted or binary PDF");
  it was retrieved as a raw file and converted with `pdftotext -layout`
  instead. The raw PDF is archived at `data/raw/ril/` precisely so this
  extraction can be independently re-verified.
* No new pipeline node, port node, or refinery node was created. `PORT016`
  (Sikka) and `R022`/`R023` (both already in `refineries.csv`, unmodified
  per this step's regression requirement) were reused as-is.

---

## Phase 3, step 2: R023 (Jamnagar SEZ) crude receipt path

<a id="phase-3-step-2-r023-jamnagar-sez-crude-receipt-path"></a>

Step 2 re-opened the `R023` ("RPL (SEZ), Jamnagar") question left
`PARTIALLY RESOLVED` by step 1, per this step's own instruction to determine
whether `R023` has a distinct crude path, a documented shared path with
`R022`, or insufficient evidence either way — and specifically not to create
an edge merely because the two refineries sit in the same physical complex.

### What step 1 had not examined

Step 1's registry note for `SRC040` (RIL's compiled MoEFCC half-yearly
compliance filing) stated that SPM/SBM/COT conditions were "recorded only
against the original refinery proposal sections" and that the filing's
"separate SEZ-refinery proposal sections carry no such marine/crude
condition" — but this conclusion was drawn from only two of the filing's five
bundled proposals (the two original-refinery proposals, `J-11011/25/94-IA-II`
and `J-11011/25/93-IA-II`) plus the dedicated SEZ proposal
(`J-11011/149/2007-IA-II`). It did not examine the filing's **third**
proposal, `J.11011/232/2005-IA-II (I)`, "Environmental clearance for
expansion and modernization of petrochemical refinery complex", which step
1's own evidence table had already correctly identified as **complex-wide
(DTA + SEZ)** by its reported capacity, but whose Marine/Coastal conditions
were not individually read.

### The new evidence

Re-reading this proposal's full condition list (`data/raw/ril/ril_jmd_ec_compliance_2024-12.txt`,
lines 743-1238) found Condition 12 (Marine/Coastal):

> "The extension of the existing tank farm shall be designed in such a way
> that the residual flow including floor washing do not percolate to the
> marine areas. The augmentation and expansion of the marine facilities like
> product berths, **Crude and product SPMs**, seawater intake channel and
> outfall shall be done in consultation with the National Institute of
> Oceanography."

RIL's own compliance response: "The augmentation and expansion of the marine
facilities has been carried out in consultation with NIO." — i.e. reported as
completed, not merely proposed.

This is qualitatively different from what step 1 found in the SEZ-specific
2009 EIA (`SRC041`), which named only product/seawater facilities in common.
Here, an RIL EC compliance filing explicitly names **crude-handling SPMs**
("Crude and product SPMs", not "product SPMs" alone) among the marine
facilities of this proposal.

### Why this proposal is read as covering R023

Four independent points establish that this proposal's "complex" includes the
SEZ refinery, not the DTA refinery alone:

1. **Capacity arithmetic.** This proposal's Production Capacity table records
   a single line item, "Crude Oil Processing Capacity: 59.7" MMTPA. The same
   compiled filing's second proposal records the DTA refinery's
   then-capacity as "18 to 27" MMTPA, and its fourth proposal (the dedicated
   SEZ proposal) records "Jamnagar Export Refinery (JERP) (already under
   implementation) ... 580" Kbpsd crude. 27 MMTPA (DTA, at that time) plus
   the JERP figure is consistent with 59.7 MMTPA; 59.7 MMTPA is not
   consistent with the DTA refinery alone at any capacity this project's
   sources record for it (current PPAC capacity is 33.0 MMTPA).
2. **Filing location.** This proposal's entity address is "Village
   Meghpar/Padana, Tehsil Lalpur Taluka" — a village pairing that appears
   nowhere else in the filing's original-refinery proposals (which give no
   village), but which RIL's own postal/pincode registrations independently
   identify as the Reliance Jamnagar SEZ site (e.g. "M/S RELIANCE INDUSTRIES
   LIMITED UNIT OF RELIANCE JAMNAGAR SEZ VILLAGE MEGAPAR PADANA TALUKA LALPUR
   DIST JAMNAGAR").
3. **Step 1's own classification.** Step 1's evidence table already labelled
   this proposal "complex-wide (DTA + SEZ)" based on the same capacity
   reasoning, before step 2 read its individual conditions.
4. **A single shared marine operator.** Gujarat Maritime Board's
   captive-jetty register (`SRC010`, already the source for `PORT016` and for
   `NL022`) lists every Sikka SPM and berth under one operator, "M/s Reliance
   Ports & Terminal Ltd." (two SBMs, SPM Nos. 3/4/5, a 4th tanker berth, a 5th
   product-jetty berth) — with no entry distinguishing a DTA-only facility
   from an SEZ-only facility. Reliance is documented as running one shared
   marine terminal company at Jamnagar, not two.

### Edge decision

**`NL023` (`PORT016` Sikka → `R023` "RPL (SEZ), Jamnagar") was added** on
this basis. `R023`'s status moves from `PARTIALLY RESOLVED` to `RESOLVED
(shared crude marine facility)`.

This is deliberately the minimum edge the evidence supports, per the
decision tree this step was given (decision-tree branch 1: "receives crude
through the same marine facility as `R022`"), and it is **not** the same
thing as "the two refineries are in the same complex" — the edge rests on a
condition that names crude-handling SPMs specifically, tied by capacity
arithmetic and filing-location evidence to a proposal covering the combined
complex, not on the refineries' shared postal address or general proximity.

**CAVEATS preserved in the edge's own notes field (see `network_links.csv`
`NL023`):**

1. Condition 12 itself does not name "Sikka" or "Vadinar" — the locality
   match to `PORT016` rests on RPTL/Sikka being the only Reliance-operated
   crude-capable marine facility documented anywhere in this project's
   sources for Jamnagar, not on a sentence in this proposal naming the
   locality.
2. The 59.7 MMTPA capacity match is an arithmetic inference across three
   proposals in the same compiled filing, not a sentence stating the
   equality outright.
3. Gujarat Maritime Board's register does not label any individual RPTL SPM
   as carrying crude versus product, so **which specific SPM unit(s) serve
   `R023` versus `R022` is not resolved** by this edge — only the
   shared-facility relationship and shared operator are established. A
   future step could pursue RPTL's own filings (if any exist and are
   retrievable) to resolve this at the individual-SPM level.

### Decision-tree classification (per this step's instructions)

| Question | Answer |
| --- | --- |
| Distinct crude import terminal for `R023`? | No evidence found. |
| Documented shared crude-receipt infrastructure with `R022`? | **Yes** — Condition 12 of `J.11011/232/2005-IA-II (I)`. |
| Insufficient evidence? | No — superseded by the above. |
| Decision-tree branch | 1: "receives crude through the same marine facility as `R022`." |
| Canonical node for that facility | `PORT016` (Sikka), reused from `NL022`; not independently re-derived from Condition 12 alone (see caveat 1 above). |

### `SRC040` registry correction

`data/reference/source_registry.csv`'s `SRC040` note has been corrected to
record that step 1's characterisation of the filing's SPM/SBM/COT conditions
("recorded only against the original refinery proposal sections") did not
account for Condition 12 of the third, combined-complex proposal, and that
this condition is the additional source for `NL023`. The correction is
appended to the existing note rather than replacing it, preserving the
original (still-accurate, for the two proposals it actually examined)
finding about the original-refinery and dedicated-SEZ proposal sections.

### What was investigated and not used

* The filing's fifth proposal (SEZ expansion, 35.2 to 41 MMTPA,
  `IA/GJ/IND2/79902/2018`) and the "Augmentation of Seawater Intake and
  Desalination Facilities at Sikka" and "Expansion of existing jetty by
  setting a new berth at Gulf..." proposals later in the same filing were
  read in full for this step; none contains a crude-specific SPM, SBM, COT,
  or pipeline condition distinct from what is already recorded above — their
  Marine/Coastal conditions concern diffusers, dredging, CRZ compliance and
  product-jetty construction, not crude intake.
* Gujarat Maritime Board's live captive-jetties page (`https://gmbports.org/captive-jetties`)
  was re-fetched directly to check for any entry distinguishing DTA-owned
  from SEZ-owned SPMs at Sikka; none exists. No new source registration was
  needed since `SRC010` already covers this page.
* No new pipeline, port, or refinery node was created. `refineries.csv` was
  not modified, per this step's regression requirement.
