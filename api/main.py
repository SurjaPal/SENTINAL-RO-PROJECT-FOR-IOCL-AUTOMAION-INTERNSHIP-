import asyncio
import json
import logging
import random
import os
import psycopg2
from psycopg2.extras import RealDictCursor
try:
    from google import genai
except ImportError:
    genai = None
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sentinel-RO Live API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ComplaintPayload(BaseModel):
    complaint_id: str
    ro_id: str
    raw_text: str

class ChatPayload(BaseModel):
    message: str
    session_id: str = "default_session"

def get_db_connection():
    try:
        conn = psycopg2.connect("dbname=sentinel user=sentinel password=sentinel host=timescaledb")
        return conn
    except Exception as e:
        logger.error(f"DB Connection failed: {e}")
        return None

def fetch_latest_telemetry():
    """Fetches the latest reading from TimescaleDB and maps it to UI expectations."""
    conn = get_db_connection()
    if not conn:
        return None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT temperature_c, volume_ltr, density, water_level_mm 
                FROM atg_readings 
                ORDER BY time DESC 
                LIMIT 1;
            """)
            row = cur.fetchone()
            
            if not row:
                return None

            temp = float(row['temperature_c'] or 82.4)
            volume = float(row['volume_ltr'] or 450.2)
            water = float(row['water_level_mm'] or 1.0)
            
            # The simulator gives us real temp and volume.
            # We map volume to "flow" contextually for the UI, and generate synthetic
            # related metrics (vibration, energy, TDS) to preserve the UI design.
            
            metrics = [
                {
                    "id": "TEMP",
                    "label": "CORE TEMPERATURE",
                    "value": f"{temp:.1f}°C",
                    "trend": "+1.2%",
                    "status": "nominal" if temp < 90 else "critical",
                    "baseValue": temp
                },
                {
                    "id": "PRES",
                    "label": "SYSTEM PRESSURE",
                    "value": f"{(volume / 1000) + 12:.1f} PSI", # synthetic mapping
                    "trend": "-0.4%",
                    "status": "nominal",
                    "baseValue": (volume / 1000) + 12
                },
                {
                    "id": "FLOW",
                    "label": "FEED FLOW RATE",
                    "value": f"{volume:.1f} L/M",
                    "trend": "+2.1%",
                    "status": "nominal",
                    "baseValue": volume
                },
                {
                    "id": "TDS",
                    "label": "PERMEATE TDS",
                    "value": f"{(water * 10) + 140:.0f} PPM", # synthetic
                    "trend": "-5.4%",
                    "status": "nominal",
                    "baseValue": (water * 10) + 140
                },
                {
                    "id": "VIBE",
                    "label": "MOTOR VIBRATION",
                    "value": f"{random.uniform(2.1, 2.5):.2f} mm/s", # synthetic jitter
                    "trend": "+0.1%",
                    "status": "nominal",
                    "baseValue": 2.4
                },
                {
                    "id": "PWR",
                    "label": "ENERGY CONSUMPTION",
                    "value": f"{random.uniform(410, 420):.1f} kW", # synthetic
                    "trend": "-1.8%",
                    "status": "nominal",
                    "baseValue": 412.0
                }
            ]
            return metrics
    except Exception as e:
        logger.error(f"Error fetching telemetry: {e}")
        return None
    finally:
        conn.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/complaints/webhook")
def receive_complaint(payload: ComplaintPayload):
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed"}
    
    try:
        with conn.cursor() as cur:
            now = datetime.now(timezone.utc)
            cur.execute("""
                INSERT INTO complaints (complaint_id, time, ro_id, raw_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (complaint_id) DO NOTHING;
            """, (payload.complaint_id, now, payload.ro_id, payload.raw_text))
            conn.commit()
        return {"status": "success", "message": "Complaint ingested"}
    except Exception as e:
        logger.error(f"Error inserting complaint: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

@app.get("/api/anomalies")
def get_anomalies(limit: int = 10):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT time, ro_id, sensor_type, value, reason 
                FROM anomalies 
                ORDER BY time DESC 
                LIMIT %s;
            """, (limit,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}")
        return []
    finally:
        conn.close()

@app.get("/api/complaints")
def get_complaints(limit: int = 10):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT time, complaint_id, ro_id, raw_text, processed_at
                FROM complaints 
                ORDER BY time DESC 
                LIMIT %s;
            """, (limit,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching complaints: {e}")
        return []
    finally:
        conn.close()

@app.get("/api/triage-suggestions")
def get_triage_suggestions(limit: int = 10):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT time, ro_id, complaint_id, complaint_category, suggested_root_cause, confidence, priority, evidence
                FROM triage_suggestions 
                ORDER BY time DESC 
                LIMIT %s;
            """, (limit,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching triage suggestions: {e}")
        return []
    finally:
        conn.close()

@app.get("/api/dispatch-tickets")
def get_dispatch_tickets(limit: int = 10):
    conn = get_db_connection()
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT time, ticket_id, ro_id, part_name, status
                FROM dispatch_tickets 
                ORDER BY time DESC 
                LIMIT %s;
            """, (limit,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching dispatch tickets: {e}")
        return []
    finally:
        conn.close()

def save_chat_message(session_id: str, role: str, content: str):
    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_memory (time, session_id, role, content)
                VALUES (%s, %s, %s, %s)
            """, (datetime.now(timezone.utc), session_id, role, content))
            conn.commit()
    except Exception as e:
        logger.error(f"Error saving chat: {e}")
    finally:
        conn.close()

def get_chat_history(session_id: str, limit: int = 10):
    conn = get_db_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT role, content 
                FROM chat_memory 
                WHERE session_id = %s
                ORDER BY time DESC 
                LIMIT %s
            """, (session_id, limit))
            rows = cur.fetchall()
            return list(reversed([dict(row) for row in rows]))
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        return []
    finally:
        conn.close()

@app.post("/api/chat")
def handle_chat(payload: ChatPayload):
    save_chat_message(payload.session_id, "user", payload.message)
    
    anomalies = get_anomalies(limit=3)
    dispatch_tickets = get_dispatch_tickets(limit=3)
    triage = get_triage_suggestions(limit=3)
    chat_history = get_chat_history(payload.session_id, limit=5)
    
    history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history])
    
    context = (
        f"Recent Anomalies:\n{json.dumps(anomalies, default=str)}\n\n"
        f"Recent Dispatch Tickets:\n{json.dumps(dispatch_tickets, default=str)}\n\n"
        f"Recent Triage Complaints:\n{json.dumps(triage, default=str)}\n"
    )
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not genai:
        return {"response": "System Error: Gemini API Key not found. Ensure it is set in .env."}
        
    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            "You are Sentinel-RO's built-in AI assistant for a fuel station operator. "
            "Respond in a friendly, conversational tone. "
            "You have memory of previous conversations in this session. If the user introduces themselves, remember their name and details in subsequent messages. "
            "If the user greets you or asks a general question, just greet them back friendly and DO NOT list any system data. "
            "ONLY use the live system data provided below to answer if the user specifically asks about anomalies, tickets, complaints, or status. "
            "Keep the answer concise, natural, and directly address the user's question.\n\n"
            "UI CONTROL: If the user asks you to navigate to the overview page, append <ACTION:NAVIGATE:/> to the very end of your response. "
            "If they ask to navigate to the dashboard, append <ACTION:NAVIGATE:/dashboard>. "
            "If they ask you to scroll to or show a specific section (kpi, charts, feed, matrix, infrastructure), append <ACTION:SCROLL_TO:section_name>. "
            "For example: 'Sure, I will show you the fleet matrix now. <ACTION:SCROLL_TO:matrix>'\n\n"
            f"LIVE SYSTEM DATA (Only use if relevant to the user's question):\n{context}\n\n"
            f"CONVERSATION HISTORY:\n{history_text}\n\n"
            f"USER CURRENT MESSAGE: {payload.message}"
        )
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
        )
        ai_text = response.text.strip()
        save_chat_message(payload.session_id, "ai", ai_text)
        return {"response": ai_text}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"response": "Sorry, I am currently unable to process your request."}

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")
    try:
        while True:
            # Poll DB every 1.5 seconds to match UI jitter rate
            metrics = fetch_latest_telemetry()
            if metrics:
                await websocket.send_text(json.dumps(metrics))
            await asyncio.sleep(1.5)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
