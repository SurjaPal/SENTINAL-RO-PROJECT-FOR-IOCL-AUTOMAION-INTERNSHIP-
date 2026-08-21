# Sentinel-RO — Week 1-2: schema + ingestion

This is the first slice of the 8-week MVP roadmap from the project proposal:
**"Reproduce FDS schema; stand up ingestion + TimescaleDB."** It's meant to be
run locally, prove the pipeline end to end on synthetic data, and give
Weeks 3-4 (the anomaly-watch module) real tables to query against.

## What's actually been tested, and what hasn't

Being upfront about this because it matters for how much to trust the code
before you build on it:

- **Tested, passing (30/30):** the data-generation logic in
  `simulator/telemetry_simulator.py` and the message-parsing/row-shaping
  logic in `ingestion/direct_mqtt_to_timescale.py`, including one
  integration-style test that inserts and queries back synthetic rows
  against an in-memory SQLite database. Run it yourself:
  `python -m unittest discover tests -v`
- **Written but NOT executed:** the actual MQTT publish/subscribe path, the
  live TimescaleDB writes, the Kafka bridge/sink, and `docker-compose.yml`
  as a whole. The sandbox this was built in couldn't reach either PyPI or
  the Ubuntu package mirrors when I tried to install mosquitto, postgresql,
  paho-mqtt, or confluent-kafka (both returned 403s from the network
  policy) — and there's no Docker in that sandbox either. So the pure logic
  is verified; the live-service wiring is not, yet.

**Do the smoke test below before trusting this with anything real.**

## Setup

```bash
cp .env.example .env
docker compose up -d
pip install -r requirements.txt
```

Give TimescaleDB a few seconds to run `schema/001_init.sql` on first boot
(it auto-runs anything in `schema/` via the `docker-entrypoint-initdb.d`
mount). Check it landed:

```bash
docker compose exec timescaledb psql -U sentinel -d sentinel -c "\dt"
```

You should see 8 tables: `retail_outlets`, `atg_readings`, `atg_alarms`,
`du_alarms`, `connectivity_alarms`, `psp_parameters`, `iot_device_health`,
`aip_stock_snapshots`.

Seed a couple of ROs (the schema's foreign keys need these to exist first):

```bash
docker compose exec timescaledb psql -U sentinel -d sentinel -c "
INSERT INTO retail_outlets (ro_id, ro_name, state, region_tier) VALUES
  ('RO1000', 'Sentinel Demo Outlet 1', 'West Bengal', 'municipal'),
  ('RO1001', 'Sentinel Demo Outlet 2', 'Jharkhand', 'within_100km');
"
```

## Smoke test (do this first)

Terminal 1 — start ingestion:
```bash
python ingestion/direct_mqtt_to_timescale.py --broker localhost
```

Terminal 2 — start the simulator against just those 2 ROs you seeded:
```bash
python simulator/telemetry_simulator.py --broker localhost --ros 2
```

Terminal 1 should start printing `[ingest] running totals: {...}` every
~50 messages. After a minute, confirm rows actually landed:

```bash
docker compose exec timescaledb psql -U sentinel -d sentinel -c \
  "SELECT count(*) FROM atg_readings;"
```

If that count is climbing, the pipeline works and you're ready for Week 3-4.
If `direct_mqtt_to_timescale.py` throws on startup, it's almost certainly a
`psycopg2` connection string mismatch with whatever you changed in
`docker-compose.yml` — check `SENTINEL_DB_DSN` in `.env` against the
Postgres service's actual host/port.

## Two ingestion paths — which one to run

- **`ingestion/direct_mqtt_to_timescale.py`** — MQTT straight to TimescaleDB.
  Simpler, fewer moving parts, what the smoke test above uses. Good enough
  for Weeks 1-6.
- **`ingestion/kafka_pipeline/`** — MQTT → Kafka (via Redpanda) → TimescaleDB,
  matching the proposal's original tech stack. Switch to this once you
  actually need more than one independent consumer reading the same
  stream — e.g. once Module 1's scorer and Module 3's anomaly watcher both
  need the fault-alert stream without double-subscribing to MQTT. Both
  scripts import the *same* row-shaping functions from the direct path, so
  there's no logic to re-write when you switch — just run
  `bridge_mqtt_to_kafka.py` and `sink_kafka_to_timescale.py` instead of
  `direct_mqtt_to_timescale.py`, pointed at the `redpanda` service.

## What the simulator generates

Six message categories over MQTT, topic-shaped `iocl/{ro_id}/{category}[/{sub_id}]`,
matching the field names in `schema/001_init.sql` (traced back to the Phase 11
FDS — see the proposal, Section 4):

| Category | Table | Real-world cadence | Demo cadence |
|---|---|---|---|
| `atg` | `atg_readings` | ~60s | 5s |
| `atg_alarm` | `atg_alarms` | event-based | ~2% chance per tick |
| `du_alarm` | `du_alarms` | event-based | ~1% chance per tick |
| `psp` | `psp_parameters` | periodic | every tick |
| `iot` | `iot_device_health` | periodic | every tick |
| `aip` | `aip_stock_snapshots` | 30 min | 60s |

Pass `--anomaly-rate` to the simulator to control how often it injects a
short-delivery-style stock variance or a battery-degradation pattern — those
are there on purpose, for Week 3-4 and Week 5-6 to have something real to
detect. Default is 0.03 (3%).

## Week 3-4: Module 3 — reconciliation anomaly watch

Lives in `analytics/module3_anomaly_watch/`. Two detectors, matching the
proposal's cold-start plan:

- **`StatisticalBaselineDetector`** — a rolling z-score per (RO, tank) on
  `variance_ltr`. Needs no training phase; it's the one you can turn on
  from day one.
- **`IsolationForestDetector`** — multivariate, over `variance_ltr`,
  `variance_pct`, and `delta_variance_ltr`. Unsupervised (no labels
  needed) but does need an explicit `.fit()` on a window of mostly-normal
  history before it can score anything.

### What's tested here (unlike Week 1-2, this one's for real)

pandas, scikit-learn, and scipy all turned out to be pre-installed in the
sandbox this was built in, so — unlike the MQTT/Kafka/Postgres pieces —
**the actual detection logic has been run, not just unit-tested in
isolation.** `python -m unittest discover tests -v` runs 46 tests total,
16 of them new for Module 3, all passing.

More usefully, `analytics/module3_anomaly_watch/evaluate.py` builds a
labeled synthetic dataset (reusing the Week 1-2 simulator, which already
tags ground truth), fits both detectors on a 300-snapshot history window,
and scores a held-out 200-snapshot live window. Actual numbers from this
run:

| Detector | Precision | Recall | F1 |
|---|---|---|---|
| Statistical baseline | 1.0 | 0.647 | 0.786 |
| Isolation Forest | 1.0 | 1.0 | 1.0 |

Run it yourself: `python -m analytics.module3_anomaly_watch.evaluate`
(from the repo root).

**Two honest caveats on those numbers, before you put them in a slide:**

1. The synthetic anomalies are a big, clean gap — normal variance sits
   within about ±15 L, injected anomalies are 150-400 L. Real short-delivery
   or meter-drift patterns may sit much closer to the noise floor, and both
   precision and recall (especially the Isolation Forest's perfect 1.0)
   will likely look worse on real data. Re-run this evaluation against real
   historical AIP data before trusting these numbers for anything.
2. Building this surfaced a genuine IsolationForest pitfall worth knowing
   about: an early version of the test trained on a near-constant tank
   level (so `variance_pct` became an exact scalar multiple of
   `variance_ltr` — two of the three features were secretly duplicates) and
   used a tiny, near-discrete oscillation as "normal." Isolation Forest
   scored an obvious 400 L outlier as *completely normal* against that
   degenerate history. Switching to Gaussian-noise history and breaking the
   feature collinearity fixed it immediately — see the comments in
   `tests/test_module3_anomaly_watch.py` (`test_fitted_on_normal_data_flags_a_clear_outlier`).
   The lesson: Isolation Forest can behave strangely on low-variance,
   collinear training data — sanity-check its scores against real telemetry
   before trusting it, not just against a clean synthetic set.

### What's NOT tested here

`run_batch.py`'s live TimescaleDB reads/writes (`pd.read_sql`,
`cursor.executemany`) — same reason as Week 1-2, no live Postgres reachable
in this sandbox. `rows_to_insert()`, the pure function it hands off to, is
tested directly instead. Smoke-test `run_batch.py` for real once you've got
a few hours of simulator data flowing into `aip_stock_snapshots` via the
Week 1-2 pipeline:

```bash
python -m analytics.module3_anomaly_watch.run_batch --hours 1 --history-hours 6
```

### New table

`schema/002_anomaly_watch.sql` adds `reconciliation_anomalies` — run it
after `001_init.sql` (docker-compose picks up both automatically on first
boot; on an already-running database, apply it by hand:
`docker compose exec timescaledb psql -U sentinel -d sentinel -f /docker-entrypoint-initdb.d/002_anomaly_watch.sql`).

## Week 5-6: Module 1 — predictive fault alerts

Lives in `analytics/module1_fault_alerts/`. This one is a genuinely
different kind of problem from Module 3: instead of "is this reading
unusual right now," it's "will this device fail soon, based on the trend
leading up to it" — so it gets its own synthetic data generator
(`battery_trajectory.py`), simulating a realistic 3-phase battery decline
(stable → declining → critical) rather than reusing Week 1-2's simulator,
which only generates instant-in-time low-battery readings, not a shape a
model can learn a trend from.

Two detectors, same cold-start philosophy as Module 3:

- **`TrendBaselineDetector`** — rule-based: flags a device when its
  rolling voltage slope is declining *and* it's already below a watch
  level. No training phase.
- **`GradientBoostedRiskDetector`** — a supervised classifier (matches the
  "gradient-boosted failure-classification" approach named in the original
  proposal) predicting P(will hit critical within the next K readings).
  Needs a fit phase on labeled trajectories — in production those labels
  would come from e-RACTS resolution history; here, from the generator's
  own ground truth, exactly as the cold-start plan anticipated.

### Real numbers, on held-out devices never seen during training

`analytics/module1_fault_alerts/evaluate.py` builds a fleet of simulated
devices (a mix of healthy-throughout and decline-to-critical), trains on
one set of devices, and evaluates on a **completely different** set —
deliberately a device-level split, not a time-based one, because the real
test of a predictive-maintenance model is whether it generalises to
hardware it's never seen, not whether it can extrapolate one battery's own
trend a little further:

| Detector | Precision | Recall | F1 | Median lead time |
|---|---|---|---|---|
| Trend baseline | 0.744 | 0.818 | 0.779 | 50.5 readings |
| Gradient Boosted | 0.983 | 0.963 | 0.973 | 16.0 readings |

Both caught 100% of the declining test devices before they went critical
(0 missed, out of 10). Run it yourself:
`python -m analytics.module1_fault_alerts.evaluate`.

**The interesting trade-off in that table:** the simple rule-based
detector gives roughly 3x more advance warning (50 readings vs. 16) than
the trained model, at the cost of more false positives (0.744 vs 0.983
precision). That's not a bug in either detector — the Gradient Boosted
model was trained on a label defined as "within the next 15 readings," so
it naturally learned to fire close to that horizon; the rule-based
detector has no such ceiling and can fire the moment its slope/threshold
condition is met, however early that turns out to be. Worth deciding
deliberately which trade-off Sentinel-RO actually wants in production —
more warning time with more noise, or tighter precision closer to the
event — rather than assuming the fancier model is strictly better.

**Two honest caveats, matching Module 3's:**

1. These numbers are on synthetic decline curves with a fixed shape. Real
   battery degradation may be noisier, non-monotonic, or influenced by
   things this generator doesn't model (ambient temperature, load cycles,
   battery age) — re-evaluate against real PSP history before trusting
   these numbers anywhere.
2. `run_batch.py` currently trains the Gradient Boosted model on
   synthetic fleet data every run, because there's no real e-RACTS-labeled
   fault history to train on yet — this is called out explicitly in that
   file's code, not hidden. Swapping in a real labeled dataset once one
   exists is the natural next step, not a rewrite.

### A structural fix worth knowing about

Adding Module 1 surfaced a real bug: `module1_fault_alerts/` and
`module3_anomaly_watch/` both have their own `features.py`, `detectors.py`,
and `evaluate.py`. The tests originally imported them by inserting each
module's directory onto `sys.path` and importing by bare name — which
works fine in isolation, but Python caches imports by module name, so
whichever test file ran first "won" the name `features` for the whole test
session, and the other module's tests failed importing things that were
never actually missing. Fixed by turning every directory into a proper
package (`__init__.py` everywhere) and importing everything by its full
dotted path (`analytics.module1_fault_alerts.features`, not `features`) —
worth keeping in mind if you add a Module 2 with its own `features.py`
later, which is exactly what's next.

### What's NOT tested here

Same shape of caveat as before: `run_batch.py`'s live TimescaleDB reads
(`psp_parameters`) and writes (`fault_alerts`) haven't run against a real
database in this sandbox. `rows_to_insert()` is tested directly instead.
Smoke-test for real once Week 1-2's pipeline has been running long enough
to accumulate PSP history:

```bash
python -m analytics.module1_fault_alerts.run_batch --hours 1 --history-hours 24
```

### New table

`schema/003_fault_alerts.sql` adds `fault_alerts`.

## Week 7-8: Module 2 — auto-triage, plus the Grafana dashboard

Lives in `analytics/module2_auto_triage/`. The roadmap scopes this one down
deliberately: **"rule-based root-cause suggestion, not full NLP yet."** So
unlike Modules 1 and 3, there's no ML model here — a keyword classifier
(`complaint_classifier.py`) buckets a complaint's free text into one of
five categories, and a rules engine (`correlator.py`) cross-references
that category against open alarms and Modules 1/3's recent output, in
priority order (a hardware alarm outranks a predictive flag, which
outranks nothing at all).

Two categories — `screen_issue` and `card_payment_issue` — are marked
`UNCORROBORATED_CATEGORIES` and deliberately always return low confidence:
Sentinel-RO's schema doesn't ingest POS/ITPS telemetry, so there's nothing
to check them against yet. Naming that gap honestly beats a confident
wrong guess.

### Evaluation: a pass rate, not precision/recall

There's no model to score against labels here, so `evaluate.py` instead
runs 10 scenarios — one per correlation rule, plus a couple of "nothing
correlates" and "uncorroborated category" cases — and reports how many
match the expected category/confidence/priority/cause. Current result:
**10/10 (100%)**, which is expected and appropriate to report plainly for
a rule-based system (I wrote the rules and the scenarios together) — but
worth being clear that this checks the rules are *internally consistent*,
not that they're *right* against real historical complaints. Re-run this
after enough real triage outcomes exist to build a proper labeled scenario
set from actual e-RACTS history, not just ones I wrote by hand.

Run it: `python -m analytics.module2_auto_triage.evaluate`

### New tables

`schema/004_auto_triage.sql` adds `complaints` (a staging table standing
in for what a real e-RACTS webhook/API integration would feed in — this
project doesn't integrate with the actual e-RACTS system, which is
IOCL-internal infrastructure) and `triage_suggestions`.

### The Grafana dashboard

`grafana/provisioning/dashboards/sentinel-ro-overview.json` — 9 panels:
4 headline stat counters (open alarms, urgent triage suggestions, flagged
fault alerts, flagged reconciliation anomalies), 2 time series (battery
voltage for at-risk ROs, reconciliation variance), and 3 tables (recent
triage suggestions, recent fault alerts, recent reconciliation anomalies).
Every SQL query in it has been checked column-by-column against the
actual schema files (see the repo history for that check) — but the
dashboard itself, like everything needing a live service, hasn't rendered
in an actual Grafana instance in this sandbox.

**A real bug this caught:** the Week 1-2 `datasources.yml` was sitting
directly in `grafana/provisioning/`, but Grafana only auto-loads
datasources from `provisioning/datasources/` specifically — one directory
level off, and it would have silently never loaded. Fixed by moving it and
giving it an explicit `uid` (`sentinel-timescaledb`) so the dashboard
panels have something stable to reference. This is exactly the kind of
thing that's easy to miss without ever having run the stack end-to-end —
another point in favor of doing that smoke test in a real Docker
environment sooner rather than later.

### What's NOT tested here

Same caveat as every other `run_batch.py` in this project — Module 2's
live TimescaleDB queries (`fetch_context`) haven't run against a real
database. `classify_complaint` and `correlate`, the actual decision logic,
are fully tested (18 tests). The Grafana dashboard hasn't rendered in a
live Grafana instance — only validated as well-formed JSON with every
column checked against the schema by hand.

## All 8 weeks: test suite total

**83 tests, all passing**, across all four pieces (ingestion, Module 3,
Module 1, Module 2): `python -m unittest discover tests -v`

## Pilot proposal

`PILOT_PROPOSAL.md` in the repo root packages the whole 8 weeks into a
short writeup — what got built, what's actually been verified vs. still
needs a live-service smoke test, and a concrete ask for a small pilot on
real ROs. That's the "package the results" step the roadmap ends on.
