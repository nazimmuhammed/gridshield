"""
GridShield - Database Layer
==============================
Explicit SQLAlchemy ORM setup - this is the real, structured database
layer for the project (SQLite file-based for local dev; the same models
work unchanged against PostgreSQL in production by just swapping the
connection string, which is a legitimate real-world deployment pattern).
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "gridshield.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class SimulationRun(Base):
    """Every cascade/reroute analysis run - your operational audit log."""
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(Integer, nullable=False)
    run_type = Column(String, nullable=False)          # "contingency" | "what_if" | "chat_triggered"
    total_failed_lines = Column(Integer)
    without_reroute_status = Column(String)
    without_reroute_max_loading = Column(Float)
    with_reroute_status = Column(String)
    with_reroute_max_loading = Column(Float)
    reroute_cost = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Explanation(Base):
    """AI-generated explanations + operator notes, per line."""
    __tablename__ = "explanations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(Integer, nullable=False)
    language = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    operator_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversationMessage(Base):
    """Dave's full chat history, per session - powers multi-turn memory."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()