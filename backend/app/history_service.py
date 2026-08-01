"""
GridShield - Simulation Run History Service
==============================================
Logs every analysis run to the database and exposes retrieval -
this is your visible "Recent Activity" audit trail.
"""

from database import SessionLocal, SimulationRun, init_db
from sqlalchemy import desc

init_db()


def log_simulation_run(line_id, run_type, cascade_data, reroute_data):
    db = SessionLocal()
    try:
        run = SimulationRun(
            line_id=line_id,
            run_type=run_type,
            total_failed_lines=cascade_data.get("total_failed_lines"),
            without_reroute_status=reroute_data["without_rerouting"].get("status"),
            without_reroute_max_loading=reroute_data["without_rerouting"].get("max_loading_pct"),
            with_reroute_status=reroute_data["with_rerouting"].get("status"),
            with_reroute_max_loading=reroute_data["with_rerouting"].get("max_loading_pct"),
            reroute_cost=reroute_data["with_rerouting"].get("total_cost"),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run.id
    finally:
        db.close()


def get_recent_runs(limit=20):
    db = SessionLocal()
    try:
        runs = db.query(SimulationRun).order_by(desc(SimulationRun.created_at)).limit(limit).all()
        return [
            {
                "id": r.id,
                "line_id": r.line_id,
                "run_type": r.run_type,
                "total_failed_lines": r.total_failed_lines,
                "without_reroute_status": r.without_reroute_status,
                "with_reroute_status": r.with_reroute_status,
                "reroute_cost": r.reroute_cost,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]
    finally:
        db.close()