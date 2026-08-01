"""
GridShield - Stage 7: Multi-Language AI Explainability Layer
================================================================
Takes structured simulation/rerouting output and generates a plain-English
(or any of 15 languages) explanation for grid operators - because a real
operator won't trust or act on a black-box number without understanding why.

Also stores operator notes alongside each explanation (SQLite), which later
feeds the chatbot (Feature #12) - giving it real memory of past decisions.
"""

import os
import sqlite3
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

LANGUAGES = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ta": "Tamil (தமிழ்)",
    "te": "Telugu (తెలుగు)",
    "bn": "Bengali (বাংলা)",
    "mr": "Marathi (मराठी)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "ar": "Arabic (العربية)",
    "zh": "Mandarin Chinese (中文)",
    "ja": "Japanese (日本語)",
    "ru": "Russian (Русский)",
    "pt": "Portuguese (Português)",
}

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "gridshield.db")


def init_db():
    """Creates the notes/explanations table if it doesn't exist yet."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id INTEGER NOT NULL,
            language TEXT NOT NULL,
            explanation TEXT NOT NULL,
            operator_note TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def build_prompt(line_id: int, cascade_data: dict, reroute_data: dict, language: str) -> str:
    """
    Builds a structured prompt from real simulation data - the LLM explains
    ACTUAL numbers from your system, it doesn't invent anything.
    """
    lang_name = LANGUAGES.get(language, "English")

    prompt = f"""You are a grid operations assistant explaining a power grid contingency event to a control room operator.

FACTS FROM THE SIMULATION (use ONLY these numbers, do not invent any other data):
- Failed transmission line: Line {line_id}
- Without any corrective action: cascade would fail {cascade_data.get('total_failed_lines')} lines total, sequence: {cascade_data.get('cascade_sequence')}
- Without rerouting: max line loading reached {reroute_data['without_rerouting'].get('max_loading_pct')}%, status: {reroute_data['without_rerouting'].get('status')}
- With AI-computed rerouting: max line loading is {reroute_data['with_rerouting'].get('max_loading_pct')}%, status: {reroute_data['with_rerouting'].get('status')}
- Rerouting generation cost: {reroute_data['with_rerouting'].get('total_cost', 'N/A')}

Write a clear, concise explanation (3-4 sentences) for a control room operator, covering:
1. What failed and what would happen if nothing is done
2. What the AI-recommended rerouting plan achieves
3. Whether the situation is now safe or still needs attention

Respond ENTIRELY in {lang_name}. Do not include any English if the language is not English. Do not add a preamble like "Here is the explanation" - just give the explanation directly."""

    return prompt


def generate_explanation(line_id: int, cascade_data: dict, reroute_data: dict, language: str = "en") -> str:
    prompt = build_prompt(line_id, cascade_data, reroute_data, language)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400,
    )
    return response.choices[0].message.content


def save_explanation(line_id: int, language: str, explanation: str, operator_note: str = None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO explanations (line_id, language, explanation, operator_note, created_at) VALUES (?, ?, ?, ?, ?)",
        (line_id, language, explanation, operator_note, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_explanation_history(line_id: int = None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if line_id is not None:
        rows = conn.execute(
            "SELECT * FROM explanations WHERE line_id = ? ORDER BY created_at DESC", (line_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM explanations ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


init_db()