"""
database.py
Handles all database operations for DepthCharge.
Sets up SQLite tables and provides save/load functions for all models.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from models import Service, Dependency, SimulationResult, RiskScore

DB_PATH = "depthcharge.db"


def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """
    Creates all tables if they don't exist yet.
    Call this once when the app starts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Table: services
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            team         TEXT NOT NULL,
            criticality  TEXT DEFAULT 'medium',
            failure_rate REAL DEFAULT 0.0,
            is_active    INTEGER DEFAULT 1
        )
    """)

    # Table: dependencies
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dependencies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id   TEXT NOT NULL,
            target_id   TEXT NOT NULL,
            weight      REAL DEFAULT 1.0,
            description TEXT DEFAULT '',
            FOREIGN KEY (source_id) REFERENCES services(id),
            FOREIGN KEY (target_id) REFERENCES services(id)
        )
    """)

    # Table: simulation_results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_results (
            run_id           TEXT PRIMARY KEY,
            triggered_by     TEXT NOT NULL,
            failed_services  TEXT NOT NULL,  -- stored as JSON list
            cascade_depth    INTEGER DEFAULT 0,
            impact_score     REAL DEFAULT 0.0,
            timestamp        TEXT NOT NULL
        )
    """)

    # Table: risk_scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_scores (
            service_id        TEXT PRIMARY KEY,
            centrality_score  REAL DEFAULT 0.0,
            failure_risk      REAL DEFAULT 0.0,
            overall_risk      REAL DEFAULT 0.0,
            rank              INTEGER
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


# ──────────────────────────────────────────────
# SERVICE operations
# ──────────────────────────────────────────────

def save_service(service: Service):
    """Insert or replace a service in the database."""
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO services
        (id, name, team, criticality, failure_rate, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        service.id,
        service.name,
        service.team,
        service.criticality,
        service.failure_rate,
        int(service.is_active)
    ))
    conn.commit()
    conn.close()


def get_all_services() -> List[Service]:
    """Fetch all services from the database."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM services").fetchall()
    conn.close()
    return [
        Service(
            id=row["id"],
            name=row["name"],
            team=row["team"],
            criticality=row["criticality"],
            failure_rate=row["failure_rate"],
            is_active=bool(row["is_active"])
        )
        for row in rows
    ]


def get_service(service_id: str) -> Optional[Service]:
    """Fetch a single service by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM services WHERE id = ?", (service_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return Service(
        id=row["id"],
        name=row["name"],
        team=row["team"],
        criticality=row["criticality"],
        failure_rate=row["failure_rate"],
        is_active=bool(row["is_active"])
    )


# ──────────────────────────────────────────────
# DEPENDENCY operations
# ──────────────────────────────────────────────

def save_dependency(dep: Dependency):
    """Insert a dependency between two services."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO dependencies (source_id, target_id, weight, description)
        VALUES (?, ?, ?, ?)
    """, (dep.source_id, dep.target_id, dep.weight, dep.description))
    conn.commit()
    conn.close()


def get_all_dependencies() -> List[Dependency]:
    """Fetch all dependencies."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM dependencies").fetchall()
    conn.close()
    return [
        Dependency(
            source_id=row["source_id"],
            target_id=row["target_id"],
            weight=row["weight"],
            description=row["description"]
        )
        for row in rows
    ]


def get_dependencies_for_service(service_id: str) -> List[Dependency]:
    """Fetch all dependencies where this service is the source."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM dependencies WHERE source_id = ?", (service_id,)
    ).fetchall()
    conn.close()
    return [
        Dependency(
            source_id=row["source_id"],
            target_id=row["target_id"],
            weight=row["weight"],
            description=row["description"]
        )
        for row in rows
    ]


# ──────────────────────────────────────────────
# SIMULATION RESULT operations
# ──────────────────────────────────────────────

def save_simulation_result(result: SimulationResult):
    """Save a simulation run result."""
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO simulation_results
        (run_id, triggered_by, failed_services, cascade_depth, impact_score, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        result.run_id,
        result.triggered_by,
        json.dumps(result.failed_services),
        result.cascade_depth,
        result.impact_score,
        result.timestamp.isoformat()
    ))
    conn.commit()
    conn.close()


def get_simulation_result(run_id: str) -> Optional[SimulationResult]:
    """Fetch a simulation result by run ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM simulation_results WHERE run_id = ?", (run_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return SimulationResult(
        run_id=row["run_id"],
        triggered_by=row["triggered_by"],
        failed_services=json.loads(row["failed_services"]),
        cascade_depth=row["cascade_depth"],
        impact_score=row["impact_score"],
        timestamp=datetime.fromisoformat(row["timestamp"])
    )


def get_all_simulation_results() -> List[SimulationResult]:
    """Fetch all simulation results."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM simulation_results ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return [
        SimulationResult(
            run_id=row["run_id"],
            triggered_by=row["triggered_by"],
            failed_services=json.loads(row["failed_services"]),
            cascade_depth=row["cascade_depth"],
            impact_score=row["impact_score"],
            timestamp=datetime.fromisoformat(row["timestamp"])
        )
        for row in rows
    ]


# ──────────────────────────────────────────────
# RISK SCORE operations
# ──────────────────────────────────────────────

def save_risk_score(score: RiskScore):
    """Save or update a risk score for a service."""
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO risk_scores
        (service_id, centrality_score, failure_risk, overall_risk, rank)
        VALUES (?, ?, ?, ?, ?)
    """, (
        score.service_id,
        score.centrality_score,
        score.failure_risk,
        score.overall_risk,
        score.rank
    ))
    conn.commit()
    conn.close()


def get_all_risk_scores() -> List[RiskScore]:
    """Fetch all risk scores ordered by rank."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM risk_scores ORDER BY rank ASC"
    ).fetchall()
    conn.close()
    return [
        RiskScore(
            service_id=row["service_id"],
            centrality_score=row["centrality_score"],
            failure_risk=row["failure_risk"],
            overall_risk=row["overall_risk"],
            rank=row["rank"]
        )
        for row in rows
    ]
