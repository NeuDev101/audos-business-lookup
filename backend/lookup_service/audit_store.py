"""SQLite-based audit store for run-level audit logging."""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Any

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "audit_store.db")


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the audit database schema."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                user TEXT NOT NULL,
                count INTEGER NOT NULL,
                ruleset_version TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                business_id TEXT,
                name TEXT,
                address TEXT,
                registration_status TEXT,
                error TEXT,
                timestamp TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_results_run_id ON results(run_id)")
        conn.commit()
    finally:
        conn.close()


def start_run(run_id: str, user: str, count: int, ruleset_version: str, source: str):
    """Start a new audit run."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO runs (run_id, user, count, ruleset_version, source) VALUES (?, ?, ?, ?, ?)",
            (run_id, user, count, ruleset_version, source)
        )
        conn.commit()
    finally:
        conn.close()


def record_result(run_id: str, result: Dict[str, Any]):
    """Record a result for a run."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO results (run_id, business_id, name, address, registration_status, error, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                result.get("business_id"),
                result.get("name") or result.get("company_name"),
                result.get("address"),
                result.get("registration_status"),
                result.get("error"),
                result.get("timestamp"),
            )
        )
        conn.commit()
    finally:
        conn.close()


def get_run_metadata(run_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a run."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT run_id, user, count, ruleset_version, source, created_at FROM runs WHERE run_id = ?",
            (run_id,)
        ).fetchone()
        if row:
            return {
                "run_id": row["run_id"],
                "user": row["user"],
                "count": row["count"],
                "ruleset_version": row["ruleset_version"],
                "source": row["source"],
                "created_at": row["created_at"],
            }
        return None
    finally:
        conn.close()


def get_run_results(run_id: str) -> List[Dict[str, Any]]:
    """Get all results for a run."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT business_id, name, address, registration_status, error, timestamp
               FROM results WHERE run_id = ? ORDER BY id""",
            (run_id,)
        ).fetchall()
        return [
            {
                "business_id": row["business_id"],
                "name": row["name"],
                "address": row["address"],
                "registration_status": row["registration_status"],
                "error": row["error"],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]
    finally:
        conn.close()

