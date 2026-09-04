"""
Sentinel-RO — Module 2 (Phase 3 Upgrade): LLM-powered complaint classifier.

Uses Google Gemini to parse free-text e-RACTS complaints into rigid categories
that the deterministic correlator can process. If the API key is missing or the
call fails, it degrades gracefully to the Phase 2 keyword matcher.
"""
from __future__ import annotations

import os
import logging
from pydantic import BaseModel

try:
    from google import genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

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
        "overcharged", "amount mismatch", "variance", "dip reading",
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

UNCORROBORATED_CATEGORIES = {"screen_issue", "card_payment_issue"}

class ComplaintClassification(BaseModel):
    category: str

def classify_with_keyword_fallback(text: str) -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return category
    return "unclassified"

def classify_complaint(text: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not genai:
        logger.warning("GEMINI_API_KEY or google-genai not found. Falling back to keyword matcher.")
        return classify_with_keyword_fallback(text)
        
    try:
        client = genai.Client(api_key=api_key)
        
        prompt = (
            "You are an AI triaging fuel station complaints. "
            f"Categorize the following complaint into exactly one of these categories: "
            f"{list(CATEGORY_KEYWORDS.keys()) + ['unclassified']}. "
            "If it does not fit neatly into one, return 'unclassified'.\n\n"
            f"Complaint text: '{text}'"
        )
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': ComplaintClassification,
                'temperature': 0.1,
            },
        )
        
        category = response.parsed.category if response.parsed else "unclassified"
        if category not in CATEGORY_KEYWORDS and category != "unclassified":
            return "unclassified"
        
        return category
        
    except Exception as e:
        logger.error(f"Gemini API failed: {e}. Falling back to keyword matcher.")
        return classify_with_keyword_fallback(text)
