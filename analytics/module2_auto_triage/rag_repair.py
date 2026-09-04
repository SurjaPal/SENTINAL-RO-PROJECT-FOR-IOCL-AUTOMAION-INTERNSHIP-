"""
Sentinel-RO — Module 2 (RAG Upgrade)
Uses Gemini to generate step-by-step repair instructions based on the suggested root cause and a local knowledge base.
"""
from __future__ import annotations

import os
import json
import logging
from pathlib import Path

try:
    from google import genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

KB_PATH = Path(__file__).resolve().parent / "repair_manual.json"

def get_repair_instructions(root_cause: str) -> str:
    """Uses Gemini to synthesize repair instructions based on the manual context."""
    if not os.path.exists(KB_PATH):
        return "Repair manual not found."

    try:
        with open(KB_PATH, "r") as f:
            manual = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load repair manual: {e}")
        return "Failed to load repair manual."

    # Retrieve context
    context = manual.get(root_cause)
    if not context:
        return "No standard repair procedure found in the knowledge base for this issue. Proceed with manual diagnostics."

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not genai:
        logger.warning("GEMINI_API_KEY or google-genai not found. Returning raw context.")
        return context

    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            f"You are an expert fuel station repair technician. "
            f"Given the root cause and the engineering manual excerpt below, "
            f"generate a concise, professional step-by-step repair plan. "
            f"Use clear bullet points or numbered steps (e.g. 1., 2., 3.). Mention any spare parts needed.\n\n"
            f"ROOT CAUSE: {root_cause}\n\n"
            f"MANUAL EXCERPT: {context}"
        )

        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )

        if response.text:
            return response.text.strip()
        return context
    except Exception as e:
        logger.error(f"Gemini RAG failed: {e}. Returning raw context.")
        return context
