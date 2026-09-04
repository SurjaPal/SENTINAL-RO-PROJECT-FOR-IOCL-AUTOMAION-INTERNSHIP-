"""
Sentinel-RO — Module 5 (Logistics Engine)
Scans recent triage suggestions, uses Gemini to extract required spare parts,
checks mock inventory, and generates dispatch tickets for zero-touch resolution.
"""
from __future__ import annotations

import os
import json
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path

try:
    from google import genai
except ImportError:
    genai = None

import psycopg2

INVENTORY_PATH = Path(__file__).resolve().parent / "inventory.json"
INSERT_TICKET = (
    "INSERT INTO dispatch_tickets (time, ticket_id, ro_id, part_name, status) "
    "VALUES (%s, %s, %s, %s, %s)"
)

def get_inventory():
    if not os.path.exists(INVENTORY_PATH):
        return {}
    with open(INVENTORY_PATH, "r") as f:
        return json.load(f)

def save_inventory(inv):
    with open(INVENTORY_PATH, "w") as f:
        json.dump(inv, f, indent=4)

def extract_parts_via_llm(text: str) -> list[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not genai:
        return []
        
    client = genai.Client(api_key=api_key)
    prompt = (
        "Extract a JSON array of string values representing exactly the spare parts "
        "listed under '**Required Spare Parts:**' in the text below. "
        "Remove quantities (like '1x', '4x') from the name, returning only the exact part name like 'Pulse Meter Unit (Part #PM-400)'. "
        "Only output the JSON array, no markdown.\n\n"
        f"TEXT: {text}"
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        if response.text:
            text_cleaned = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(text_cleaned)
    except Exception as e:
        print(f"Failed to extract parts: {e}")
    return []

def run(dsn: str):
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Get the latest triage suggestion that has "🔧 REPAIR PLAN"
    cursor.execute(
        "SELECT ro_id, suggested_root_cause FROM triage_suggestions "
        "WHERE suggested_root_cause LIKE '%REPAIR PLAN%' "
        "ORDER BY time DESC LIMIT 1"
    )
    row = cursor.fetchone()
    if not row:
        print("[module5] No triage suggestions with repair plans found.")
        return
        
    ro_id, text = row
    
    parts = extract_parts_via_llm(text)
    if not parts:
        print("[module5] No parts extracted.")
        return
        
    inventory = get_inventory()
    
    for part in parts:
        # Match part loosely
        matched_key = None
        for k in inventory.keys():
            if k in part or part in k:
                matched_key = k
                break
                
        if matched_key and inventory[matched_key] > 0:
            # Dispatch
            inventory[matched_key] -= 1
            ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
            cursor.execute(INSERT_TICKET, (
                datetime.now(timezone.utc),
                ticket_id,
                ro_id,
                matched_key,
                "DISPATCHED"
            ))
            print(f"[module5] Generated DISPATCH TICKET {ticket_id} for {matched_key} to {ro_id}.")
        else:
            print(f"[module5] Part {part} is OUT OF STOCK.")
            
    save_inventory(inventory)
    print("[module5] Logistics batch complete.")

def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO Module 5 Logistics")
    parser.add_argument("--dsn", default=os.environ.get("SENTINEL_DB_DSN",
                         "dbname=sentinel user=sentinel password=sentinel host=localhost"))
    args = parser.parse_args()
    run(args.dsn)

if __name__ == "__main__":
    main()
