# EnergyShield AI — MVP Demo Dashboard

An MVP demonstration / decision-support prototype over the data already built
in `data/reference/` and `data/processed/`. This is **not** a production
system — see the DEMO MODE badge in the app itself and the caveats on every
screen.

## Run

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

## Structure

```
dashboard/
├── app.py                 # entry point, sidebar nav, demo walkthrough mode
├── data_loader.py          # reads data/reference + data/processed CSVs
├── analytics.py            # network graph, KPIs, live validation checks
├── scenario_engine.py      # demo disruption scenarios over the real graph
├── styles.css               # dark command-center theme
├── components/
│   ├── ui.py                # header, badges, KPI cards
│   └── map_view.py           # India network map (plots only geolocated nodes)
├── pages/                   # one module per screen
│   ├── screen1_command_center.py
│   ├── screen2_resilience.py
│   ├── screen3_infrastructure.py
│   ├── screen4_routes.py
│   ├── screen5_scenario.py
│   ├── screen6_data_trust.py
│   └── screen7_roadmap.py
└── test_smoke.py            # import/render smoke tests, no live browser needed
```

## Screens

1. **Executive Command Center** — KPIs, layer status, network map, Jamnagar
   hero cards.
2. **Network Resilience** — connected components, isolated nodes, ranked
   refinery connectivity.
3. **Infrastructure** — tabbed tables for refineries/ports/pipelines/reserves.
4. **Routes & Chokepoints** — modelled corridors, computed distances,
   chokepoint baseline flows.
5. **Demo Scenario Simulator** — Hormuz / Red Sea / port / refinery
   disruption walkthroughs computed from the live network graph.
6. **Data Trust** — source registry, trust categories, validation summary.
7. **AI Roadmap** — current / next / later capability plan (not implemented).

## Smoke tests

```bash
python dashboard/test_smoke.py
```

Verifies: data loads, the network graph builds, the app starts without
exception, all seven screens render without exception, and the scenario
engine runs for every scenario.
