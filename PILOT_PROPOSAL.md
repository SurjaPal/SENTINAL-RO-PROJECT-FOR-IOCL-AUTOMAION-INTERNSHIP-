# Sentinel-RO — Pilot Proposal

*8-week MVP build complete. This is the ask: a small, low-risk pilot on real Retail Outlets.*

---

## The ask, in one line

Run Sentinel-RO's three modules read-only, in shadow mode, against **5-10 live
ROs already on the CROC/IoT architecture (Phase 11)** for **4 weeks**, and
compare its flags against what the ACC and field officers already caught
manually — no changes to any control system, no dealer-facing changes, nothing
that touches dispensing.

## What got built (8 weeks, 4 pieces, 83 passing tests)

| Piece | What it does | Status |
|---|---|---|
| Schema + ingestion | Mirrors the Phase 11 FDS telemetry fields in TimescaleDB; MQTT→Kafka→DB pipeline | Logic fully unit-tested; live broker/DB not yet smoke-tested (see below) |
| Module 3 — reconciliation anomaly watch | Flags stock variances a fixed threshold would miss | Evaluated on synthetic data: 1.0 precision / 1.0 recall (Isolation Forest), 1.0 / 0.65 (statistical baseline) |
| Module 1 — predictive fault alerts | Flags battery/PSP decline before the hard alarm fires | Evaluated on held-out synthetic devices: 0.98 precision / 0.96 recall, 16-reading median lead time (Gradient Boosted); 0.74 / 0.82, 50-reading lead time (rule-based) |
| Module 2 — auto-triage | Suggests root cause + priority for an incoming complaint | 10/10 scenario pass rate (rule-based, not yet NLP — see roadmap) |
| Grafana dashboard | 9 panels surfacing all three modules' output | JSON validated, columns checked against schema; not yet rendered live |

## What's actually proven vs. what still needs a real environment

Being direct about this, because it matters for what the pilot needs to
confirm first:

**Proven — the decision logic is right.** Every module's core logic (feature
engineering, detectors, the correlation rules) has been unit-tested, and for
Modules 1 and 3 specifically, evaluated end-to-end against labeled synthetic
data with real precision/recall/lead-time numbers, not just "the code runs."

**Not yet proven — how it performs on real telemetry.** All of the numbers
above are on synthetic data with a clean signal (injected anomalies well
separated from normal noise). Real short-delivery patterns, real battery
degradation, and real complaint text will likely be messier. This is
*exactly* what the shadow-mode pilot is for — it's the cheapest way to find
out before anything is trusted to auto-raise a ticket.

**Not yet run live at all.** The sandbox this was built in couldn't reach
either PyPI or the Ubuntu package mirrors to install MQTT/Postgres/Kafka, so
the ingestion pipeline, the live database writes, and the Grafana dashboard
have been written and validated as far as static analysis allows, but never
actually executed end-to-end against live services. **The first step of any
pilot has to be the smoke test in README.md, on a real machine, before
anything else** — this is a known, explicitly flagged gap, not a hidden one.

## Why shadow mode, and why 5-10 ROs

- **Shadow mode** (log predictions, raise nothing automatically) matches the
  risk mitigation in the original proposal — false positives from an
  unvalidated model erode ACC trust fast, and there's no way to know the real
  false-positive rate without watching it run against real data first.
- **5-10 ROs** is enough to see all three modules produce real output within
  4 weeks without needing sign-off for a larger data-access scope than an
  intern-led pilot can reasonably ask for.
- **Already on CROC (Phase 11)** because that's the only architecture
  generation with the full IoT telemetry set this schema assumes — piloting
  against an older FCC-era RO would mean building a compatibility layer
  first, which isn't a good use of a 4-week pilot window.

## What "success" looks like at the end of 4 weeks

1. The ingestion pipeline ran continuously without silent data loss (the
   smoke test in README.md, sustained).
2. Module 3's flagged reconciliation anomalies were manually checked against
   what dip-record audits already knew — did it catch anything real, and how
   many false alarms per week.
3. Module 1's fault alerts were checked against any PSP/battery complaints
   that came in during the window — did an alert precede the complaint, and
   by how long.
4. Module 2's suggested root causes were shown to (not acted on by) the ACC
   for a sample of real complaints, and rated for usefulness.
5. A go/no-go call on whether to move any module out of shadow mode.

## What this deliberately does not ask for

No production write access, no changes to CROC, no dealer-facing anything,
no auto-raised e-RACTS tickets during the pilot — this is a listening-only
extension to infrastructure that already exists, evaluated against a small,
reversible slice of it.
