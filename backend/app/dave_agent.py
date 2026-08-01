"""
GridShield - Dave: Agentic Tool-Calling Chatbot
==================================================
Dave is a conversational agent with real tool access:
- Can run live simulations on demand
- Can retrieve past decision history (RAG over explanations/notes)
- Can send real SMS/WhatsApp alerts via Twilio to configured contacts
- Maintains multi-turn conversation memory per session

Design note: send_alert targets PRE-CONFIGURED contacts (set in .env),
not arbitrary numbers - this mirrors how real alerting systems work
(confirmed contact lists, not free-form messaging to any number).

Safety note: send_alert includes a code-level dedup guard so a
re-triggered tool call (e.g. the LLM misinterpreting a follow-up
question) can't accidentally re-fire a real alert. Prompt instructions
alone aren't reliable enough for an action with real-world side effects.
"""

import os
import json
import sqlite3
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

from grid_topology import load_ieee_grid, convert_to_networkx
from cascade_simulation import simulate_line_failure
from rerouting_optimizer import evaluate_without_rerouting, compute_rerouting_plan
from explainability import get_explanation_history

load_dotenv()

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_SMS_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")

# Pre-configured "authority" contacts - in a real deployment these would be
# actual on-call engineer / control room numbers, verified and confirmed.
ALERT_CONTACTS = {
    "on_call_engineer": os.environ.get("ALERT_CONTACT_PHONE"),
}

CRITICAL_LINES = [27, 15, 40, 29, 9]

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "gridshield.db")


def init_conversation_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_conversation_history(session_id: str, limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id ASC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


# ---------- TOOL IMPLEMENTATIONS (these call your REAL backend logic) ----------

_net = load_ieee_grid()
_G = convert_to_networkx(_net)


def tool_run_simulation(line_id: int) -> dict:
    failed_lines, _ = simulate_line_failure(_net, _G, failed_line_idx=line_id)
    return {"line_id": line_id, "total_failed_lines": len(failed_lines), "cascade_sequence": failed_lines}


def tool_run_reroute(line_id: int) -> dict:
    baseline = evaluate_without_rerouting(_net, line_id)
    rerouted = compute_rerouting_plan(_net, line_id)
    return {"line_id": line_id, "without_rerouting": baseline, "with_rerouting": rerouted}


def tool_get_past_decisions(line_id: int) -> dict:
    history = get_explanation_history(line_id)
    return {"line_id": line_id, "past_decisions": history[:5]}  # last 5


def tool_list_critical_lines() -> dict:
    return {"critical_lines": CRITICAL_LINES,
            "note": "These lines historically cause the largest cascades in N-1/N-2 analysis."}


# Tracks recently sent alerts to prevent duplicate real-world sends
# (in-memory is fine for a single dev process / demo)
_recent_alerts = {}  # key: session_id -> datetime
ALERT_DEDUP_WINDOW_SECONDS = 300  # 5 minutes


def tool_send_alert(message: str, channel: str = "whatsapp", urgency: str = "normal",
                     _session_id: str = None) -> dict:
    """
    Sends a REAL SMS or WhatsApp message via Twilio to the pre-configured
    on-call contact. This is real agentic action, not a simulated response.

    Includes a dedup guard: if the same session sends an alert again within
    ALERT_DEDUP_WINDOW_SECONDS, the send is skipped rather than re-fired.
    This protects against the LLM misfiring the tool on a follow-up turn
    (e.g. a recall question) - prompt instructions alone aren't a reliable
    enough safeguard for something with a real-world side effect.
    """
    recipient = ALERT_CONTACTS.get("on_call_engineer")
    if not recipient:
        return {"status": "FAILED", "reason": "No alert contact configured in .env (ALERT_CONTACT_PHONE)"}

    if not TWILIO_SID or not TWILIO_TOKEN:
        return {"status": "FAILED", "reason": "Twilio credentials not configured in .env"}

    dedup_key = _session_id
    now = datetime.utcnow()
    last_sent = _recent_alerts.get(dedup_key)
    if last_sent and (now - last_sent).total_seconds() < ALERT_DEDUP_WINDOW_SECONDS:
        return {"status": "SKIPPED", "reason": "Duplicate alert already sent recently - not re-sending."}

    try:
        client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        prefix = "🚨 GRIDSHIELD ALERT" if urgency == "high" else "GridShield Notice"
        full_message = f"{prefix}: {message}"

        if channel == "whatsapp":
            sent = client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                to=f"whatsapp:{recipient}",
                body=full_message,
            )
        else:
            sent = client.messages.create(
                from_=TWILIO_SMS_NUMBER,
                to=recipient,
                body=full_message,
            )
        _recent_alerts[dedup_key] = now
        return {"status": "SENT", "channel": channel, "sid": sent.sid}
    except Exception as e:
        return {"status": "FAILED", "reason": str(e)}


# ---------- TOOL SCHEMA (tells the LLM what tools exist and their params) ----------

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_simulation",
            "description": "Runs a live cascade failure simulation for a specific transmission line. Returns which lines would fail if this line fails and no corrective action is taken.",
            "parameters": {
                "type": "object",
                "properties": {"line_id": {"type": "integer", "description": "Line ID, 0-40"}},
                "required": ["line_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_reroute",
            "description": "Computes the AI rerouting/optimization plan for a specific line failure, showing if it can be fixed and at what cost.",
            "parameters": {
                "type": "object",
                "properties": {"line_id": {"type": "integer", "description": "Line ID, 0-40"}},
                "required": ["line_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_past_decisions",
            "description": "Retrieves past AI explanations and operator notes previously recorded for a specific line.",
            "parameters": {
                "type": "object",
                "properties": {"line_id": {"type": "integer", "description": "Line ID, 0-40"}},
                "required": ["line_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_critical_lines",
            "description": "Returns the known list of historically critical/dangerous transmission lines in this grid.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_alert",
            "description": "Sends a real SMS or WhatsApp alert to the configured on-call engineer/authority contact. Use this when the operator explicitly asks to notify, alert, or text someone about a grid event IN THIS message. Never use this for recall/memory questions about past conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The alert message content"},
                    "channel": {"type": "string", "enum": ["sms", "whatsapp"], "description": "Which channel to send via - default to whatsapp unless the user explicitly asks for SMS/text"},
                    "urgency": {"type": "string", "enum": ["normal", "high"], "description": "Urgency level - affects message prefix"},
                },
                "required": ["message", "channel"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "run_simulation": tool_run_simulation,
    "run_reroute": tool_run_reroute,
    "get_past_decisions": tool_get_past_decisions,
    "list_critical_lines": tool_list_critical_lines,
    "send_alert": tool_send_alert,
}

SYSTEM_PROMPT = """You are Dave, an AI operations assistant embedded in GridShield, a power grid resilience monitoring system.

You help grid control room operators by:
- Running live simulations and rerouting analysis when asked
- Retrieving past decisions/notes about specific lines
- Sending real SMS/WhatsApp alerts to the on-call engineer when explicitly asked to notify someone
- Answering questions about grid state using ONLY real data from your tools - never invent numbers

Be concise, professional, and precise - like a competent control room colleague, not a chatty assistant.
When you use a tool, base your response entirely on its actual output.
Only call send_alert when the operator clearly asks you to notify, alert, or message someone in THIS message - never re-trigger it based on past conversation history.
Do not call any tool if the operator is just asking a simple recall/memory question (e.g. "what did we just discuss") - answer directly from conversation history instead."""


def chat_with_dave(session_id: str, user_message: str) -> dict:
    save_message(session_id, "user", user_message)
    history = get_conversation_history(session_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=TOOLS_SCHEMA,
        tool_choice="auto",
        temperature=0.3,
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    tools_used = []

    if tool_calls:
        messages.append({
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ],
        })
        for call in tool_calls:
            fn_name = call.function.name
            fn_args = json.loads(call.function.arguments)
            if fn_name == "send_alert":
                fn_args["_session_id"] = session_id
            result = TOOL_FUNCTIONS[fn_name](**fn_args)
            tools_used.append({"tool": fn_name, "args": fn_args, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, default=str),
            })

        final_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.3,
        )
        final_text = final_response.choices[0].message.content
    else:
        final_text = response_message.content

    save_message(session_id, "assistant", final_text)

    return {"response": final_text, "tools_used": tools_used}


init_conversation_db()