from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(os.getenv("PROMPTCRAFT_DB_PATH", "data/promptcraft.db"))


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                experiment_type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL
            )
            """
        )


def save_experiment(experiment_id: str, created_at: str, request: dict[str, Any], response: dict[str, Any]) -> None:
    with _connect() as connection:
        connection.execute(
            "INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?)",
            (
                experiment_id,
                created_at,
                request["experiment_type"],
                request["prompt"],
                json.dumps(request),
                json.dumps(response),
            ),
        )


def list_experiments(limit: int = 20) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT id, created_at, experiment_type, prompt, response_json FROM experiments ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    items = []
    for row in rows:
        response = json.loads(row["response_json"])
        items.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "experiment_type": row["experiment_type"],
                "prompt": row["prompt"],
                "winner": response.get("winner"),
                "providers": [result["provider"] for result in response.get("results", [])],
            }
        )
    return items


def get_experiment(experiment_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT request_json, response_json FROM experiments WHERE id = ?", (experiment_id,)
        ).fetchone()
    if not row:
        return None
    return {"request": json.loads(row["request_json"]), "response": json.loads(row["response_json"])}


def delete_experiment(experiment_id: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
    return cursor.rowcount > 0

