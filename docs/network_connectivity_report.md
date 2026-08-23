# Network Connectivity Report — Phase 2, Step 5 (amended Phase 3, Steps 1-2)

**Date:** 2026-08-23 (Phase 2 step 5); amended 2026-08-23 (Phase 3 step 1 —
Jamnagar edge `NL022` added; Phase 3 step 2 — Jamnagar edge `NL023` added; see
the note at the end of §3 and the new §4b entry for `R022`/`R023`)
**Scope:** the reference network graph only — `refineries.csv`, `ports.csv`,
`strategic_reserves.csv`, `pipelines.csv` as nodes, `network_links.csv` as
edges. `routes.csv` / `route_nodes.csv` (the modelled international corridor
layer) are deliberately **excluded**: they describe how crude might reach an
Indian port from abroad, not the domestic refinery/port/pipeline/reserve
network this report analyses.

**Method:** `data/validation/validate_network_connectivity.py` loads the four
node datasets and the one edge dataset, builds an undirected adjacency graph
(direction in `network_links.csv` records who evidences the connection, not a
one-way physical constraint), and computes connected components and isolated
nodes. It is a reporting tool, not a pass/fail gate — an isolated node is very
often the correct, honest state of a sourced graph. Re-run it after any change
to `network_links.csv` and re-check this report still agrees:

```bash
python data/validation/validate_network_connectivity.py
```

---

## 1. Node counts by type

| Node type | Count | Source dataset |
| --- | ---: | --- |
| Refinery | 24 | `refineries.csv` |
| Port | 18 | `ports.csv` |
| Pipeline | 5 | `pipelines.csv` |
| Reserve | 5 | `strategic_reserves.csv` |
| **Total** | **52** | |

## 2. Edge counts by type

| `link_type` | Count |
| --- | ---: |
| `pipeline_to_refinery` | 8 |
| `port_to_refinery` | 9 |
| `port_to_pipeline` | 3 |
| `reserve_to_refinery` | 3 |
| **Total edges** | **23** |

(Phase 3 step 1 added one `port_to_refinery` edge, `NL022` `PORT016` Sikka →
`R022` "RIL, Jamnagar". Phase 3 step 2 added a second, `NL023` `PORT016`
Sikka → `R023` "RPL (SEZ), Jamnagar"; see
[`docs/data_sources.md`](data_sources.md#phase-3-step-1-jamnagar-network-connectivity)
and [`docs/data_sources.md`](data_sources.md#phase-3-step-2-r023-jamnagar-sez-crude-receipt-path).)

No `refinery_to_port`, `refinery_to_pipeline`, `pipeline_to_port`,
`reserve_to_port`, `reserve_to_pipeline`, `port_to_reserve` or
`pipeline_to_reserve` edge exists yet — every sourced edge found so far runs
"downstream" (port → pipeline/refinery, pipeline → refinery, reserve →
refinery). This is a property of what has been *found and sourced*, not an
assertion that flow is one-directional.

## 3. Connected components

23 edges connect 32 of the 52 nodes into **9 connected components** ranging
from 2 to 8 nodes. 20 nodes have zero edges (§4).

| # | Nodes | Members |
| --- | ---: | --- |
| 1 | 8 | `PL001` Salaya–Mathura Pipeline, `PL003` Mundra–Panipat Pipeline, `PL004` Mundra–Bathinda Pipeline, `PORT015` Mundra Port, `R003` IOC Koyali, `R006` IOC Mathura, `R007` IOC Panipat, `R020` HMEL GGSR |
| 2 | 5 | `PL002` Paradip–Haldia–Barauni Pipeline, `PORT012` Paradip Port, `R004` IOC Barauni, `R005` IOC Haldia, `R009` IOC Paradip |
| 3 | 4 | `PORT006` New Mangalore Port, `R019` MRPL Mangalore, `SPR002` Mangaluru SPR, `SPR003` Padur SPR |
| 4 | 3 | `PORT003` Mumbai Port, `R010` HPC Mumbai, `R012` BPC Mumbai |
| 5 | 3 | `PORT011` Visakhapatnam Port, `R011` HPC Visakh, `SPR001` Visakhapatnam SPR |
| 6 | 3 | `PORT016` Sikka, `R022` RIL Jamnagar, `R023` RPL (SEZ) Jamnagar |
| 7 | 2 | `PL005` Vadinar–Bina Pipeline, `R014` BPC Bina |
| 8 | 2 | `PORT009` Chennai Port, `R015` CPCL Manali |
| 9 | 2 | `PORT002` Vadinar Offshore Oil Terminal, `R024` NEL Vadinar |

Component 1 is the largest because `PL001` (three refinery endpoints: Koyali,
Mathura, Panipat) and `PORT015` Mundra (feeding both `PL003` and `PL004`) share
members. Components 7 and 9 both sit at Vadinar but are **separate
components**: `PL005`'s Vadinar intake and `PORT002`'s Vadinar Offshore Oil
Terminal are exactly the unresolved endpoint conflict this project has left
open since Phase 2 step 2 (see §5) — merging them would mean guessing the
answer the evidence review deliberately declined to guess.

**Component 6 grew from 2 to 3 nodes in Phase 3 step 2**: `NL022` (step 1)
connects `PORT016` (Sikka) to `R022` ("RIL, Jamnagar") on Reliance Industries
Limited's own MoEFCC compliance filing for its original Jamnagar refinery.
`NL023` (step 2) now also connects `PORT016` to `R023` ("RPL (SEZ),
Jamnagar"): a Marine/Coastal condition under the same compiled filing's
combined-complex expansion proposal (59.7 MMTPA, DTA+SEZ) names "Crude and
product SPMs" among the marine facilities augmented for that combined
capacity, corroborated by Gujarat Maritime Board's register showing a single
shared operator (Reliance Ports & Terminal Ltd.) running every Sikka SPM/berth
with no DTA/SEZ distinction. This is a narrower finding than "the two
refineries share a marine terminal" would be on its own — it rests on an
explicit crude-SPM condition tied to the combined-complex EC, not on
geographic proximity. See
[`docs/data_sources.md`](data_sources.md#phase-3-step-1-jamnagar-network-connectivity)
and
[`docs/data_sources.md`](data_sources.md#phase-3-step-2-r023-jamnagar-sez-crude-receipt-path).

## 4. Isolated nodes (0 edges) — 20 of 52

### 4a. Ports (10 isolated)

| Port | Why it has no edge |
| --- | --- |
| `PORT001` Deendayal Port | Every sourced Vadinar crude edge attaches to the **constituent terminal** `PORT002`, not to the parent port record. `ports.csv` states the SBM/OOT crude facilities are at Vadinar; no source states a crude edge to Deendayal Port's own (non-Vadinar) jetties. |
| `PORT004` Jawaharlal Nehru Port | A BPCL tender describing a JNPT liquid-cargo jetty exists but names no refinery and has no `source_url`/date/archived copy meeting this project's provenance bar (Phase 2 step 3 finding). Recorded as a lead, not evidence. |
| `PORT005` Mormugao Port | `crude_handling = unknown` — no crude statement located at all. |
| `PORT007` Cochin Port | `crude_handling = unknown` — the Phase 1 case where an inferred `yes` (from the presence of an SPM) was rejected by the validator and corrected. Still no source. |
| `PORT008` V.O. Chidambaranar Port | `crude_handling = unknown` — source names other cargo classes, not crude. |
| `PORT010` Kamarajar Port | `crude_handling = unknown` — source names "POL" generically, which is not crude specifically per this project's rule. |
| `PORT013` Syama Prasad Mookerjee Port Kolkata | `crude_handling = unknown` for the port as a whole; no refinery/pipeline edge sourced. |
| `PORT014` Haldia Dock Complex | `crude_handling = unknown`. IOC Haldia refinery (`R005`) **is** connected, but through `PL002` from Paradip — no source attributes Haldia refinery's crude receipt to the Haldia Dock Complex port itself. |
| `PORT017` Vadhavan Port | Not operational — notified but not yet built. Correctly isolated. |
| `PORT018` Galathea Bay Port | Not operational — under development, stated role is container transhipment, not crude. Correctly isolated. |

`PORT016` Sikka is **no longer isolated** as of Phase 3 step 1 — see `NL022`
in §3, component 6. The unresolved `PL005` Sikka/Vadinar locality conflict
(§5) is unaffected: it concerns which port record holds BORL's SPM, a
question separate from the sourced Reliance SPM edges to `R022` and `R023`.

### 4b. Refineries (8 isolated)

| Refinery | Why it has no edge |
| --- | --- |
| `R001` IOC Digboi, `R002` IOC Guwahati, `R008` IOC Bongaigaon | `PL002`'s own operator sentence explicitly excludes these: Bongaigaon is reached through **Oil India Limited's** pipeline (not `PL002`) and Guwahati by **rail rake** — neither is a `PL002` edge, and no OIL pipeline record exists in `pipelines.csv` to carry one. Digboi was never named in any pipeline evidence considered. |
| `R013` BPC Kochi | No marine or pipeline crude-receipt source has been investigated for this refinery in any Phase 2 or Phase 3 step so far — an **unexamined gap**, not a closed one. |
| `R016` CPCL, Cauvery Basin | `0.0 MMTPA`, not in operation. Correctly isolated; retained as a valid non-operating record per Phase 1 rules. |
| `R017` NRL Numaligarh | The Paradip–Numaligarh Crude Pipeline (PNCPL) that would connect it is **under construction**, not commissioned, and no readable official operator page describes it. Explicitly out of scope per the Phase 2 step 2 evidence-gap list. |
| `R018` ONGC Tatipaka | Smallest refinery (0.066 MMTPA); no crude-receipt source investigated — an unexamined gap. |
| `R021` HRRL Pachpadra | Newest refinery in the master; no crude-receipt source investigated — an unexamined gap. |

`R022` RIL Jamnagar and `R023` RPL (SEZ) Jamnagar are **no longer isolated**
— see `NL022` and `NL023` in §3, component 6. `R023` was investigated
separately from `R022` in both Phase 3 steps, per the standing instruction not
to assume identical connectivity between the two Jamnagar refinery units
without evidence: step 1 found only shared product/seawater infrastructure
(insufficient for an edge) and left `R023` "PARTIALLY RESOLVED"; step 2 found
a Marine/Coastal condition naming "Crude and product SPMs" under the same
compiled filing's combined-complex (DTA+SEZ) expansion proposal, sufficient
to source `NL023`. See
[`docs/data_sources.md`](data_sources.md#phase-3-step-2-r023-jamnagar-sez-crude-receipt-path)
for the full evidence and its caveats — in particular, which specific Sikka
SPM unit(s) carry crude for `R023` versus `R022` is **not** resolved by this
edge; only the shared-facility relationship is.

### 4c. Strategic reserves (2 isolated)

| Reserve | Why it has no edge |
| --- | --- |
| `SPR004` Chandikhol | Approved, not commissioned. Correctly isolated — no connection can be operational at a facility that does not yet exist. |
| `SPR005` Padur (Phase II) | Same reason; a separate, not-yet-built expansion at the Padur locality, not to be merged with the commissioned `SPR003`. |

## 5. Isolated *edges that were deliberately not added*, not isolated nodes

Two node **pairs** remain formally unresolved rather than isolated by omission
— the graph is missing a specific edge, not blind to the relationship:

- **`PL001` (Salaya–Mathura Pipeline)** has no port endpoint. Its marine
  intake's location and operator (Vadinar, IndianOil, two SPM systems) are
  established; the specific port record is not, because no source reconciles
  IndianOil's count of two SPMs with MoPNG-PS&W's count of three SBMs at
  Vadinar under `PORT002`. Formally `PARTIALLY RESOLVED` (Phase 2 steps 2 and
  4). `PL001` itself is **not** isolated — it has 3 downstream refinery edges
  (`R003`, `R006`, `R007`); only its upstream marine-intake edge is missing.
- **`PL005` (Vadinar–Bina Pipeline)** has no port endpoint for the same
  reason in reverse: one BORL facility is published under two different
  locality labels (Vadinar by BPCL/BORL, Sikka by Gujarat Maritime Board), and
  no document reconciles them. Formally `PARTIALLY RESOLVED`. `PL005` **is**
  connected downstream to `R014` (BPC, Bina); only its upstream edge is
  missing.

Neither gap was closed by this step, per the standing instruction not to
reopen the `PL001`/`PL005` investigation without genuinely new evidence, and
none was found. **No edge was added anywhere in this report's production** —
this is a read-only analysis of the graph as Phase 2 steps 1–4 left it.

## 6. Known limitations

1. **Undirected analysis.** `network_links.csv` records direction as "who
   evidences the connection," not a hydraulic flow direction; this report
   treats every edge as bidirectional for the purpose of counting components.
   A future flow model must not assume a component's internal connectivity
   implies flow can run either way through every edge.
2. **The graph excludes `routes.csv`.** International corridors (Persian Gulf,
   UAE, Saudi, Russia, West Africa, Brazil, US) are a separate, explicitly
   modelled layer and are not nodes or edges in this component analysis. A
   future combined view would need to decide how a `routes.csv` destination
   port joins onto this domestic graph.
3. **32 of 52 nodes participate in the graph; 20 do not.** That is a
   statement about what has been *sourced*, not about what physically exists.
   Ports with `crude_handling = unknown` (§4a) and refineries with no
   examined crude-receipt source (§4b) are gaps to close, not findings of "no
   connection."
4. **`R022` (RIL, Jamnagar) and `R023` (RPL (SEZ), Jamnagar) are both now
   connected** (`NL022`, Phase 3 step 1; `NL023`, Phase 3 step 2) — these are
   the two largest refineries in the country. The two edges rest on different
   conditions within the same compiled MoEFCC filing (SPM/SBM/COT conditions
   on the original-refinery proposals for `R022`; a "Crude and product SPMs"
   condition on the combined-complex expansion proposal for `R023`), and
   neither edge resolves which specific Sikka SPM unit(s) carry crude for
   which refinery — see §4b and
   [`docs/data_sources.md`](data_sources.md#phase-3-step-1-jamnagar-network-connectivity)
   and
   [`docs/data_sources.md`](data_sources.md#phase-3-step-2-r023-jamnagar-sez-crude-receipt-path)
   for what was and was not established.
5. **Component 1 and Component 2's size is partly a modelling artefact** of
   how many refineries a single trunk pipeline happens to serve (`PL001`
   serves three, `PL002` serves two) rather than evidence of unusually dense
   physical infrastructure at those locations.
6. **No edge in this graph carries a volume, capacity-utilisation or
   direction-of-flow claim.** Connectivity here means "a sourced physical or
   operational relationship exists," nothing more — see the caveats already
   recorded in `docs/data_dictionary.md` for `network_links.csv`.
