import json
import sqlite3
from pathlib import Path
from typing import Any

from advisory.snack_recommender import recommend_better_snacks


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
        record["personalized_advice"] = _clean_personalized_advice(result)
        record["recommendation_status"] = _recommendation_status(result)
        record["snack_recommendations"] = _snacks_from_result(result)
        records.append(record)
    return records


def _important_from_result(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    if result.get("important_ingredients"):
        return result["important_ingredients"]

    important = {"hazards": [], "good": []}
    for item in result.get("matched", []):
        matched_name = item.get("matched_ingredient", "")
        if not matched_name or matched_name == "No good match found":
            continue

        score = float(item.get("health_score") or 0)
        cautions = item.get("caution_conditions") or []
        ingredient = {
            "name": matched_name,
            "ocr_name": item.get("ocr_ingredient", matched_name),
            "score": score,
            "cautions": cautions,
        }
        if cautions or score <= 1.5:
            important["hazards"].append(ingredient)
        elif score >= 3.5:
            important["good"].append(ingredient)

    return important


def _recommendation_status(result: dict[str, Any]) -> str:
    status = result.get("recommendation_status")
    if status:
        return status

    advice = str(result.get("personalized_advice", "")).lower()
    if "no strong warning" in advice:
        return "safe"
    if "warning" in advice or "review" in advice:
        return "warning"
    return "neutral"


def _clean_personalized_advice(result: dict[str, Any]) -> str:
    advice = result.get("personalized_advice") or ""
    if "No strong warning matched your saved health profile" in advice:
        return "No strong warning for you."
    if advice.startswith("Personal warning for your profile:"):
        return advice.replace("Personal warning for your profile:", "Warning for you:", 1)
    return advice


def _snacks_from_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    if result.get("snack_recommendations"):
        return result["snack_recommendations"]

    user_conditions = []
    for recommendation in result.get("profile_recommendations", []):
        condition = recommendation.get("condition")
        if condition:
            user_conditions.append(str(condition).lower())

    recommendations = result.get("profile_recommendations") or result.get("recommendations") or []
    return recommend_better_snacks(user_conditions, recommendations)


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
    record["result"]["important_ingredients"] = _important_from_result(record["result"])
    record["result"]["personalized_advice"] = _clean_personalized_advice(record["result"])
    record["result"]["recommendation_status"] = _recommendation_status(record["result"])
    record["result"]["snack_recommendations"] = _snacks_from_result(record["result"])
    return record
