"""
GridShield - FastAPI Backend
==============================
Wires together everything built so far:
- Stage 2: Grid topology (grid_topology.py)
- Stage 3: Cascade simulation (cascade_simulation.py)
- Stage 4: N-1 / N-2 contingency analysis (contingency_analysis.py, n2_contingency.py)
- Stage 5: Rerouting optimization (rerouting_optimizer.py)

Run with: uvicorn app.main:app --reload
Then visit http://localhost:8000/docs for interactive API documentation
(FastAPI auto-generates this - genuinely useful for your resume/demo).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from explainability import LANGUAGES, generate_explanation, save_explanation, get_explanation_history

from grid_topology import load_ieee_grid, convert_to_networkx
from cascade_simulation import simulate_line_failure
from rerouting_optimizer import evaluate_without_rerouting, compute_rerouting_plan
from typing import Optional
from dave_agent import chat_with_dave
from history_service import log_simulation_run, get_recent_runs
from weather_service import get_latest_weather, start_weather_polling
import math
from datetime import datetime
from backtesting import compare_mechanism_to_gridshield


class ChatRequest(BaseModel):
    session_id: str
    message: str
app = FastAPI(title="GridShield API", version="0.1.0")

# Allow the React frontend (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://gridshield-cgy7.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the grid once at startup, keep it in memory (fine for a 30-bus system)
net = load_ieee_grid()
G = convert_to_networkx(net)
weather_scheduler = start_weather_polling()


class WhatIfRequest(BaseModel):
    line_id: int
class ExplainRequest(BaseModel):
    line_id: int
    language: str = "en"
    operator_note: Optional[str] = None


@app.get("/")
def root():
    return {
        "service": "GridShield API",
        "status": "running",
        "grid": "IEEE 30-bus test system",
        "endpoints": ["/grid-topology", "/simulate-cascade/{line_id}",
                      "/reroute/{line_id}", "/what-if"],
    }
@app.get("/backtest/{line_id}")
def backtest(line_id: int):
    failed_lines, _ = simulate_line_failure(net, G, failed_line_idx=line_id)
    cascade_dict = {"total_failed_lines": len(failed_lines), "cascade_sequence": failed_lines}
    return compare_mechanism_to_gridshield(cascade_dict)
@app.post("/chat")
def chat(request: ChatRequest):
    return chat_with_dave(request.session_id, request.message)

@app.get("/languages")
def list_languages():
    return LANGUAGES
@app.get("/stress-factors/{line_id}")
def stress_factors(line_id: int):
    weather = get_latest_weather()
    temp = weather.get("temp_c") or 25.0

    # Heat stress multiplier - transformers stress non-linearly above ~35C
    heat_multiplier = 1 + max(0, (temp - 35) / 20)

    # Simulated EV/solar stress pattern based on time of day
    hour = datetime.utcnow().hour
    ev_charging_factor = 1.15 if 18 <= hour <= 22 else 1.0  # evening EV charging peak
    solar_variability_factor = 0.9 if 10 <= hour <= 15 else 1.05  # midday solar offsets grid load

    combined_stress_multiplier = round(heat_multiplier * ev_charging_factor * solar_variability_factor, 3)

    return {
        "line_id": line_id,
        "current_temp_c": temp,
        "heat_multiplier": round(heat_multiplier, 3),
        "ev_charging_factor": ev_charging_factor,
        "solar_variability_factor": solar_variability_factor,
        "combined_stress_multiplier": combined_stress_multiplier,
        "interpretation": "Values above 1.0 indicate elevated real-world stress beyond baseline simulation assumptions",
    }

@app.post("/explain")
def explain(request: ExplainRequest):
    cascade_data = simulate_line_failure(net, G, failed_line_idx=request.line_id)
    baseline = evaluate_without_rerouting(net, request.line_id)
    rerouted = compute_rerouting_plan(net, request.line_id)

    cascade_dict = {
        "total_failed_lines": len(cascade_data[0]),
        "cascade_sequence": cascade_data[0],
    }
    reroute_dict = {"without_rerouting": baseline, "with_rerouting": rerouted}

    explanation_text = generate_explanation(
        request.line_id, cascade_dict, reroute_dict, request.language
    )
    save_explanation(request.line_id, request.language, explanation_text, request.operator_note)

    return {
        "line_id": request.line_id,
        "language": request.language,
        "explanation": explanation_text,
    }


@app.get("/explanations/{line_id}")
def get_history(line_id: int):
    return get_explanation_history(line_id)
@app.get("/weather")
def weather():
    return get_latest_weather()
@app.get("/grid-topology")
def get_grid_topology():
    """
    Returns the grid structure for frontend visualization:
    nodes (buses) and edges (lines) with their attributes.
    """
    nodes = [
        {"id": int(n), "name": str(data.get("name")), "vn_kv": data.get("vn_kv")}
        for n, data in G.nodes(data=True)
    ]
    edges = [
        {"source": int(u), "target": int(v), "max_i_ka": data.get("max_i_ka")}
        for u, v, data in G.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


@app.get("/simulate-cascade/{line_id}")
def simulate_cascade(line_id: int):
    """
    Stage 3: simulates what happens if this specific line fails,
    with no corrective action - shows the raw cascade.
    """
    failed_lines, _ = simulate_line_failure(net, G, failed_line_idx=line_id)
    return {
        "initial_failure": line_id,
        "total_failed_lines": len(failed_lines),
        "cascade_sequence": failed_lines,
    }


@app.get("/reroute/{line_id}")
def reroute(line_id: int):
    baseline = evaluate_without_rerouting(net, line_id)
    rerouted = compute_rerouting_plan(net, line_id)
    reroute_dict = {"without_rerouting": baseline, "with_rerouting": rerouted}

    cascade_data, _ = simulate_line_failure(net, G, failed_line_idx=line_id)
    cascade_dict = {"total_failed_lines": len(cascade_data)}

    log_simulation_run(line_id, "contingency", cascade_dict, reroute_dict)

    return {
        "failed_line": line_id,
        "without_rerouting": baseline,
        "with_rerouting": rerouted,
    }
@app.get("/history")
def history(limit: int = 20):
    return get_recent_runs(limit)


@app.post("/what-if")
def what_if(request: WhatIfRequest):
    """
    Stage 8: on-demand hypothetical query - operator picks any line,
    gets full analysis (cascade + rerouting) in one call.
    """
    cascade = simulate_line_failure(net, G, failed_line_idx=request.line_id)
    baseline = evaluate_without_rerouting(net, request.line_id)
    rerouted = compute_rerouting_plan(net, request.line_id)
    return {
        "line_id": request.line_id,
        "cascade_if_unaddressed": {
            "total_failed_lines": len(cascade[0]),
            "sequence": cascade[0],
        },
        "without_rerouting": baseline,
        "with_rerouting": rerouted,
    }