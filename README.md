# ⚡ GridShield

**Autonomous Grid Resilience & Load Rerouting System**

🔗 **Live Demo:** [gridshield-cgy7.vercel.app](https://gridshield-cgy7.vercel.app)
🔗 **API Docs:** [gridshield-backend.onrender.com/docs](https://gridshield-backend.onrender.com/docs)

> ⚠️ Backend is on Render's free tier — if inactive, the first request may take up to 50 seconds to wake the server. Please be patient on first load.

GridShield is a full-stack, AI-integrated platform that predicts, simulates, and actively mitigates cascading power grid failures using real AC power-flow physics, constrained optimization, and a multi-language conversational AI agent capable of taking real-world action.

Built on the IEEE 30-bus power system — a real, industry-standard test grid used in academic and utility research worldwide — GridShield does not stop at detection. It simulates the physical consequences of a failure, computes a mathematically optimal corrective solution, explains that solution in natural language across 15 languages, and can autonomously notify a human operator via real SMS/WhatsApp alerts. It closes the full **sense → simulate → decide → act → verify** loop that most monitoring tools stop short of.

---

## 📖 Table of Contents

- [The Problem](#-the-problem)
- [Core Features](#-core-features)
- [Architecture](#️-architecture)
- [Technology Stack — What & Why](#-technology-stack--what--why)
- [Key Terminology](#-key-terminology)
- [Getting Started](#-getting-started)
- [Key Findings](#-key-findings)
- [Limitations](#️-limitations)
- [Business Value](#-business-value)
- [Societal Impact](#-societal-impact)

---

## 🎯 The Problem

Power grids are networks of substations and transmission lines, each with a maximum safe load capacity. When one line fails, its load redistributes onto neighboring lines. If that push overloads a neighbor, it fails too, cascading outward. This is a **cascading failure** — the mechanism behind the **July 2012 India blackout**, which affected over **700 million people** across two days, the largest power outage in recorded history.

Most grid monitoring software stops at detection. GridShield closes the full loop.

---

## ✨ Core Features

| Feature | Description |
|---|---|
| 🔮 Risk Prediction | ML baseline (Random Forest, 98% AUC-ROC) on real UCI grid-stability data |
| ⚡ Cascade Simulation | Real AC power-flow physics via `pandapower` — not a graph approximation |
| 🔍 N-1 / N-2 Contingency Analysis | All 41 lines + all 820 line-pairs tested; found compound vulnerabilities invisible to N-1 alone |
| 🔧 Rerouting Optimization | Optimal Power Flow (OPF) — 70% overload-prevention rate |
| 🌍 Multi-Language AI Explainability | Live-data-grounded explanations in 15 languages (Groq / Llama 3.3) |
| 🤖 Dave — Agentic AI Chatbot | Tool-calling agent, RAG memory, real SMS/WhatsApp alerts via Twilio |
| 🌡️ Live Weather Integration | 15-minute polling, factored into real-time stress multipliers |
| 📊 Historical Backtesting | Validated against the 2012 India blackout case study |
| 🗄️ Full Audit Database | SQLAlchemy-backed log of every simulation, explanation, and decision |

---

## 🏗️ Architecture
Live Weather API + UCI Training Data
│
▼
Risk Model
│
▼
Grid Graph (NetworkX, IEEE 30-bus)
│
▼
Cascade Simulation (pandapower / real AC power flow)
│
▼
N-1 / N-2 Contingency Analysis
│
▼
Rerouting Optimization (OPF)
│ │ │
▼ ▼ ▼
AI Explanation Dashboard Dave (Agentic
(15 languages) (React) Chatbot + Twilio)
│ │
└──────► SQLAlchemy DB ◄─────┘
**Deployment:** React frontend on Vercel · FastAPI backend on Render · SQLite database (production-ready for PostgreSQL migration)

---

## 🛠️ Technology Stack

**Backend:** FastAPI · Python · pandapower · NetworkX · OR-Tools/OPF · SQLAlchemy · APScheduler
**Frontend:** React · Vite · Axios
**AI/LLM:** Groq (Llama 3.3 70B) — tool-calling & multi-language generation
**Integrations:** Twilio (SMS/WhatsApp) · OpenWeatherMap API
**Database:** SQLite via SQLAlchemy ORM
**Grid Data:** IEEE 30-bus standard test system · UCI Electrical Grid Stability dataset
**Deployment:** Vercel (frontend) · Render (backend)

### Why these choices?

- **pandapower over a custom graph model** — gives genuine electrical physics (Kirchhoff's laws-based power flow), not a stylized approximation. Real grid behavior depends on impedance and topology, which only a real power-flow solver captures correctly.
- **SQLAlchemy/SQLite over MongoDB** — this project's data (simulation runs, explanations, chat logs) is inherently structured and relational, exactly what SQL databases are designed for. SQLAlchemy models are database-agnostic — the same code runs against PostgreSQL in production by changing only the connection string.
- **Groq over standard GPU-hosted APIs** — free tier + significantly lower inference latency, which matters for a control-room tool where response time is a real usability factor.
- **Twilio for real alerting** — the feature that elevates Dave from a chatbot that *answers* to an agent that *acts*, a materially rarer capability in student-level AI projects.

---

## 📖 Key Terminology

- **Cascading failure** — a failure where one component's collapse increases stress on others, causing them to fail in turn.
- **N-1 / N-2 contingency analysis** — grid-reliability standards testing stability against any single (N-1) or any pair (N-2) of simultaneous component failures.
- **AC power flow** — a physics-based calculation of current/voltage/power distribution across a network, based on Kirchhoff's circuit laws.
- **Optimal Power Flow (OPF)** — a constrained optimization problem finding the generator dispatch that satisfies all safety constraints at minimum cost.
- **Tool-calling agent** — an AI system that autonomously decides to invoke external functions based on user intent, rather than only generating text.
- **RAG (Retrieval-Augmented Generation)** — retrieving stored real data to ground an AI response, rather than relying on the model's memory alone.

---

## 🚀 Getting Started

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Create `backend/.env`:
GROQ_API_KEY=your_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
ALERT_CONTACT_PHONE=+91XXXXXXXXXX
OPENWEATHER_API_KEY=your_key
Run:
```bash
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`

---

## 📊 Key Findings

- **Line 27** is the grid's most critical single point of failure — cascades to 9 total line failures.
- **Lines 10+21 and 13+21**, failing *simultaneously*, cause total grid collapse despite neither being individually dangerous — a compound vulnerability only N-2 analysis reveals.
- **Line 9's failure is structurally unfixable** via rerouting alone (153% overload persists post-optimization) — indicating a genuine infrastructure bottleneck, not a software-solvable problem.

---

## ⚠️ Limitations

- Uses the IEEE 30-bus standard test topology — real utility grid topology is confidential and not publicly available anywhere, for security reasons.
- Backtesting validates the *qualitative* cascade mechanism against the 2012 India blackout, not an exact numerical reproduction of that specific event.
- WhatsApp alerting currently uses Twilio's development sandbox (72-hour session limit); production would use Twilio's verified WhatsApp Business API.
- Renewable/EV stress factors are a time-of-day heuristic model, not trained on real utility-scale telemetry.
- Backend runs on Render's free tier — may sleep after inactivity, causing a delayed first response.

---

## 💼 Business Value

GridShield's architecture mirrors real commercial grid contingency-analysis software used by utilities — automating manual, combinatorially-scaling analysis, converting raw detection into a specific, quantified, explained corrective action, and maintaining a full auditable decision log relevant to real post-incident regulatory review processes.

## 🌍 Societal Impact

Grid reliability is a public safety issue, not an abstract engineering concern. The 2012 India blackout disrupted hospitals, water systems, and railways across 20+ states. Tools that help identify and pre-empt cascading failures before they occur have a direct connection to public welfare.

---

## 👤 Author

**Nazim Muhammed**
[LinkedIn](https://linkedin.com/in/nazim-muhammed123) · [GitHub](https://github.com/nazimmuhammed)

---

## 📄 License

MIT