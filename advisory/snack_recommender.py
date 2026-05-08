import csv
from pathlib import Path
from typing import Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
SNACK_DATASET_PATH = BASE_DIR / "data" / "snack_recommendations.csv"


def _split_tags(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split("|") if item.strip()}


def load_snack_recommendations() -> List[Dict[str, object]]:
    snacks = []
    with SNACK_DATASET_PATH.open(mode="r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            snacks.append(
                {
                    "snack_name": row["snack_name"].strip(),
                    "good_for": _split_tags(row.get("good_for", "")),
                    "avoid_for": _split_tags(row.get("avoid_for", "")),
                    "reason": row["reason"].strip(),
                    "tags": sorted(_split_tags(row.get("tags", ""))),
                }
            )
    return snacks


def recommend_better_snacks(user_conditions: List[str], recommendations: List[Dict[str, object]]) -> List[Dict[str, object]]:
    user_condition_set = {condition.lower() for condition in user_conditions}
    triggered_conditions = {
        str(recommendation.get("condition", "")).lower()
        for recommendation in recommendations
        if recommendation.get("condition")
    }
    target_conditions = triggered_conditions or user_condition_set

    ranked_snacks = []
    for snack in load_snack_recommendations():
        good_for = snack["good_for"]
        avoid_for = snack["avoid_for"]

        if user_condition_set & avoid_for:
            continue

        score = len(target_conditions & good_for) * 2 + len(user_condition_set & good_for)
        if score <= 0 and target_conditions:
            continue

        ranked_snacks.append((score, snack))

    ranked_snacks.sort(key=lambda item: (-item[0], item[1]["snack_name"]))
    return [
        {
            "snack_name": snack["snack_name"],
            "reason": snack["reason"],
            "tags": snack["tags"],
        }
        for _, snack in ranked_snacks[:4]
    ]
