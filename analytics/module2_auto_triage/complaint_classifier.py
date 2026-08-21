"""
Sentinel-RO — Module 2 (Week 7-8): complaint classifier.

The roadmap calls this out specifically as "rule-based root-cause
suggestion, not full NLP yet" — so this is deliberately a keyword matcher,
not a model. The learning guide's fastText -> Hugging Face -> IndicBERT
path is the documented upgrade route once this thin version proves the
correlation logic in correlator.py is worth the trouble — building the NLP
layer before knowing whether the correlation rules even work would be
solving the wrong problem first.

Categories are deliberately narrow and tied to what Sentinel-RO's schema
can actually corroborate (see correlator.py) — a category this classifier
can't back up with any telemetry is worse than not classifying it at all,
since a confident-looking wrong suggestion erodes ACC trust faster than an
honest "couldn't tell."
"""
from __future__ import annotations

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "no_dispensing": [
        "not dispensing", "pump not working", "nozzle stopped", "fuel not coming",
        "nozzle not working", "dispenser down", "pump down", "not pumping",
    ],
    "power_issue": [
        "power cut", "no power", "power failure", "generator", "electricity gone",
        "mains down", "current gone",
    ],
    "price_mismatch": [
        "wrong price", "price issue", "rate wrong", "price mismatch", "billed wrong",
        "overcharged", "amount mismatch",
    ],
    "screen_issue": [
        "screen blank", "display not working", "console dead", "screen not showing",
        "monitor blank", "display off",
    ],
    "card_payment_issue": [
        "card not working", "payment fail", "swipe not working", "card declined",
        "payment not going through", "transaction fail",
    ],
}

# Categories Sentinel-RO's current schema has NO telemetry table to
# corroborate against (no POS/ITPS ingestion yet — see README). Kept
# separate from CATEGORY_KEYWORDS so the classifier can still name them
# honestly rather than silently mis-bucketing them into something it can
# check, and correlator.py knows to skip straight to "needs manual
# diagnosis" for these rather than pretending to investigate.
UNCORROBORATED_CATEGORIES = {"screen_issue", "card_payment_issue"}


def classify_complaint(text: str) -> str:
    """Returns the first matching category (dict insertion order = priority
    order — no_dispensing checked first since it's the highest-revenue-impact
    category, matching the penalty structure researched for the field-officer
    briefing: dispensing-affecting downtime is penalised at a materially
    higher rate than other equipment). Returns "unclassified" if nothing
    matches — an honest miss, not a forced guess."""
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return category
    return "unclassified"
