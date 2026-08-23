# Phase 2 Report — Network Edge Layer, Connectivity and Computed Routes

**Date:** 2026-08-23
**Result:** **PASS** — Phase 1 suite (10/10), network-link validator, and
computed-route validator all exit 0.
**Scope:** Phase 2, steps 1–5.

---

## 1. What Phase 2 built, step by step

| Step | Deliverable | Status |
| --- | --- | --- |
| 1 | `pipelines.csv` (5 rows) and `network_links.csv` (first edges) | Complete |
| 2 | High-impact network gaps closed: 5 new edges (`NL017`–`NL021`), BORL Sikka/Vadinar conflict characterised | Complete |
| 3 | `ports.csv` attribute review (`refinery_connected` / `pipeline_connected` / `storage_connected`) on 4 ports touched by step 2 evidence | Complete |
| 4 | Targeted re-investigation of `PL001` / `PL005` marine-intake gaps | Complete — neither closed; both formally `PARTIALLY RESOLVED` |
| 5 | Network connectivity analysis + computed/derived route-distance layer | Complete (this report) |

## 2. Verified network links

- **21** edges in `network_links.csv`, spanning 4 `link_type`s
  (`pipeline_to_refinery` 8, `port_to_refinery` 7, `port_to_pipeline` 3,
  `reserve_to_refinery` 3).
- **5** pipelines in `pipelines.csv`; 3 of 5 have a sourced upstream (marine)
  endpoint, 2 (`PL001`, `PL005`) do not.
- Every edge resolves both endpoints **by id**, with the stored name matching
  the reference record's canonical name character for character, and every
  edge's `notes` opens `Evidence: ` and states what the source
  `Establishes: ` — enforced by `validate_network_links.py`.

## 3. Unresolved evidence gaps (unchanged by step 5)

`PL001` (Salaya–Mathura) and `PL005` (Vadinar–Bina) remain **formally
`PARTIALLY RESOLVED`**: each pipeline's marine intake location and operator
is established, but the specific `ports.csv` record it corresponds to is not,
because the two official publishers involved (IndianOil vs MoPNG-PS&W for
`PL001`; BPCL/BORL vs Gujarat Maritime Board for `PL005`) name the same
physical facility under conflicting counts or locality labels with no
reconciling document. Step 5 did **not** reopen this investigation — no
genuinely new evidence was found or sought, per the standing instruction —
and added no port endpoint to either pipeline. See
`docs/data_sources.md` for the full step 2/4 history.

The full list of candidate edges investigated and deliberately not created
(Paradip SPM ownership, `PORT004` JNPT, `PL002` → Bongaigaon/Guwahati, `PORT006`
→ `SPR002`, `SPR004`/`SPR005`, PNCPL) is unchanged from step 4 — see
`docs/data_sources.md#network-edge-evidence-gaps`.

## 4. Network connectivity (step 5, Part A)

Full detail: [`docs/network_connectivity_report.md`](network_connectivity_report.md).
Summary:

- **52 reference nodes** (24 refineries, 18 ports, 5 pipelines, 5 reserves);
  **21 edges**.
- **8 connected components** (2–8 nodes each) covering **29 of 52 nodes**.
- **23 isolated nodes**: 11 ports, 10 refineries, 2 reserves. Each is
  individually attributed in the connectivity report to either a documented
  evidence gap (e.g. `crude_handling = unknown`), a genuinely non-operational
  facility (`PORT017`/`PORT018` not built, `SPR004`/`SPR005` not
  commissioned, `R016` zero-capacity), or an **unexamined** gap flagged for
  Phase 3 (most notably `R022`/`R023` Reliance Jamnagar — India's two largest
  refineries by capacity, with zero sourced network connectivity).
- **No edge was added anywhere in step 5.** The connectivity analysis is
  read-only; closing an isolated-node count by inference is exactly the
  failure mode this project's validators exist to prevent.

## 5. Computed route layer (step 5, Parts B–C)

Two new files in `data/processed/`, strictly separate from
`data/reference/`:

- `computed_routes.csv` — 9 rows (8 routes; `RT004` has `via_suez` and
  `via_sumed` variants).
- `route_segments.csv` — 7 rows, the individual coordinate-resolvable
  geodesic sub-legs that `computed_routes.csv` sums.

**Method:** great-circle (haversine) distance, spherical Earth,
`R = 6371.0088 km`, computed only between consecutive nodes in a route's
`route_nodes.csv` sequence that both carry a sourced coordinate
(`ports.csv` or `chokepoints.csv`). `suppliers.csv` and every named export
terminal have no coordinate anywhere in this project, so **no route has a
full origin-to-destination computed distance** — every populated row is
tagged `distance_coverage = partial_last_leg_only`, and three routes
(`RT002`, `RT005`, `RT008`) have no computable segment at all. This is
stated explicitly rather than approximated.

**What this is not:** a geodesic distance is a straight line through the
Earth's surface, not a shipping-lane or navigational distance — it is never
labelled "sailing distance" anywhere in this layer. No vessel-speed or
transit-time assumption exists in this project, so `estimated_transit_days`
is `NULL` on every row, exactly as `routes.csv` has always kept it.

Full documentation: `docs/data_dictionary.md` §§13–14;
sourcing/method rationale: `docs/data_sources.md`
("Network connectivity finalisation and the computed route layer").

## 6. Validation results

```
python data/validation/validate_computed_routes.py     -> PASS (0 critical, 0 warnings)
python data/validation/validate_network_links.py        -> PASS (0 critical, 0 warnings)
python data/validation/validate_phase1.py --quiet        -> PASS (10/10 validators)
```

The computed-route validator independently **recomputes every geodesic
segment from `ports.csv`/`chokepoints.csv` coordinates** on every run and
fails if the stored value drifts from the recomputation by more than 0.5 km
— an explicit, reproducible sanity check rather than a claim taken on faith.
An additional manual spot-check confirmed `CP001` (Strait of Hormuz) to
`PORT001` (Deendayal Port) at ~1465 km and `CP006` (Cape of Good Hope) to
`PORT006` (New Mangalore Port) at ~7935 km are the right order of magnitude
for those legs.

`git diff --check` reports no whitespace errors in the changes made this
step.

## 7. Remaining limitations going into Phase 3

1. `PL001` / `PL005` marine-intake port endpoints remain unresolved — see §3.
2. 23 of 52 reference nodes carry no sourced network edge; `R022`/`R023`
   (Reliance Jamnagar) are the highest-value unexamined lead.
3. No route in `computed_routes.csv` has a full origin-to-destination
   distance — only the last coordinate-resolvable leg into India is
   computed, because `suppliers.csv` and every export terminal lack
   coordinates. Sourcing export-terminal coordinates would be the single
   highest-value improvement to this layer.
4. No vessel-speed or transit-time modelling assumption exists anywhere in
   this project; `estimated_transit_days` stays `NULL` throughout.
5. All Phase 1 limitations not touched by Phase 2 (L1–L15 in
   `docs/phase1_report.md`) still stand — most notably the 10 ports with
   `crude_handling = unknown` and the absent Urals/ESPO crude assays.

## 8. Recommendation for Phase 3

Two candidate starting points, in priority order:

1. **Investigate Reliance's Jamnagar network connectivity** (`R022`, `R023`)
   — the single largest gap between refining capacity and sourced network
   evidence in the current graph.
2. **Source coordinates for at least the named export terminals already in
   `route_nodes.csv`** (Yanbu, Fujairah, Jebel Dhanna) so the computed route
   layer can extend coverage beyond `partial_last_leg_only` for the routes
   that already have a named terminal.

Both are additive to the existing reference/processed separation and do not
require reopening `PL001`/`PL005`, building a dashboard, or starting any
dynamic (live price, AIS, forecasting, optimisation) layer — all of which
remain explicitly out of scope until the static network beneath them is more
complete.
