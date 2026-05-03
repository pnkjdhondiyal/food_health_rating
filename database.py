import json
import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "food_health.sqlite3"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                health_conditions TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scan_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_name TEXT,
                image_name TEXT,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
            """
        )


def row_to_user(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None

    user = dict(row)
    user["health_conditions"] = json.loads(user.get("health_conditions") or "[]")
    return user


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_user(row)


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return row_to_user(row)


def create_user(name: str, email: str, password_hash: str, health_conditions: list[str]) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (name, email, password_hash, health_conditions)
            VALUES (?, ?, ?, ?)
            """,
            (name.strip(), email.lower().strip(), password_hash, json.dumps(health_conditions)),
        )
        return int(cursor.lastrowid)


def update_user_conditions(user_id: int, health_conditions: list[str]) -> None:
    with get_connection() as connection:
        connection.execute(
            "UPDATE users SET health_conditions = ? WHERE id = ?",
            (json.dumps(health_conditions), user_id),
        )


def create_scan_record(
    user_id: int,
    product_name: str,
    image_name: str,
    result: dict[str, Any],
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scan_records (user_id, product_name, image_name, result_json)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, product_name.strip(), image_name, json.dumps(result)),
        )
        return int(cursor.lastrowid)


def list_scan_records(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, product_name, image_name, result_json, created_at
            FROM scan_records
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (user_id,),
        ).fetchall()

    records = []
    for row in rows:
        record = dict(row)
        result = json.loads(record["result_json"])
        record["score"] = result.get("score")
        record["classification"] = result.get("classification")
        record["rating"] = result.get("rating")
        record["personalized_advice"] = result.get("personalized_advice")
        records.append(record)
    return records


def get_scan_record(user_id: int, scan_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, product_name, image_name, result_json, created_at
            FROM scan_records
            WHERE user_id = ? AND id = ?
            """,
            (user_id, scan_id),
        ).fetchone()

    if row is None:
        return None

    record = dict(row)
    record["result"] = json.loads(record["result_json"])
    return record
