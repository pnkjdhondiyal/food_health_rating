import csv
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
NUTRIENT_PROFILES_PATH = BASE_DIR / "data" / "nutrient_profiles.csv"
NUTRIENT_LIMITS_PATH = BASE_DIR / "data" / "nutrient_limits.csv"


def _load_profiles() -> Dict[str, Dict]:
    profiles = {}
    with NUTRIENT_PROFILES_PATH.open(mode="r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = row["nutrient"].strip().lower()
            profiles[name] = {
                "unit": row["unit"].strip(),
                "low_max": float(row["low_max"]),
                "medium_max": float(row["medium_max"]),
                "high_min": float(row["high_min"]),
                "direction": row["direction"].strip(),
                "weight": float(row["weight"]),
            }
    return profiles


def _load_condition_limits() -> Dict[str, List[Dict]]:
    """Returns {nutrient: [{condition, condition_limit, condition_action}, ...]}"""
    limits: Dict[str, List[Dict]] = {}
    with NUTRIENT_LIMITS_PATH.open(mode="r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            nutrient = row["nutrient"].strip().lower()
            condition = row.get("condition", "").strip().lower()
            if not condition:
                continue
            limits.setdefault(nutrient, []).append({
                "condition": condition,
                "condition_limit": float(row["condition_limit"]),
                "condition_action": row.get("condition_action", "warn").strip(),
            })
    return limits


# Load once at module level
_PROFILES: Dict[str, Dict] = _load_profiles()
_CONDITION_LIMITS: Dict[str, List[Dict]] = _load_condition_limits()


def _score_single(value: float, profile: Dict) -> float:
    """
    Score a single nutrient value on a 0–5 scale using the profile thresholds.
    direction=lower_better: low=5, medium=3, high=1
    direction=higher_better: low=1, medium=3, high=5
    direction=neutral:       low=3, medium=3, high=2
    """
    low_max = profile["low_max"]
    medium_max = profile["medium_max"]
    direction = profile["direction"]

    if direction == "lower_better":
        if value <= low_max:
            return 5.0
        if value <= medium_max:
            # Interpolate between 5 and 3
            ratio = (value - low_max) / (medium_max - low_max)
            return round(5.0 - ratio * 2.0, 2)
        # Interpolate between 3 and 1
        ratio = min((value - medium_max) / max(medium_max, 1), 1.0)
        return round(3.0 - ratio * 2.0, 2)

    if direction == "higher_better":
        if value >= profile["high_min"]:
            return 5.0
        if value >= medium_max:
            ratio = (value - medium_max) / max(profile["high_min"] - medium_max, 1)
            return round(3.0 + ratio * 2.0, 2)
        if value >= low_max:
            ratio = (value - low_max) / max(medium_max - low_max, 1)
            return round(1.0 + ratio * 2.0, 2)
        return 1.0

    # neutral
    if value <= medium_max:
        return 3.0
    return 2.0


def _check_condition_warnings(
    nutrient: str,
    value: float,
    user_conditions: List[str],
) -> List[Dict]:
    """Return triggered condition warnings for a nutrient value."""
    warnings = []
    user_condition_set = {c.lower() for c in user_conditions}
    for limit_entry in _CONDITION_LIMITS.get(nutrient, []):
        if limit_entry["condition"] not in user_condition_set:
            continue
        if value > limit_entry["condition_limit"]:
            warnings.append({
                "condition": limit_entry["condition"],
                "nutrient": nutrient,
                "value": value,
                "limit": limit_entry["condition_limit"],
                "action": limit_entry["condition_action"],
            })
    return warnings


def calculate_nutrient_score(
    extracted_nutrients: List[Dict],
    user_conditions: Optional[List[str]] = None,
) -> Dict:
    """
    Score extracted nutrients and return a structured result.

    Returns:
        {
            "score": float | None,          # 0–5 weighted average
            "scored_nutrients": [...],       # per-nutrient breakdown
            "condition_warnings": [...],     # triggered condition alerts
            "missing_nutrients": [...],      # nutrients in profile but not found in OCR
        }
    """
    user_conditions = user_conditions or []

    # Build a quick lookup from extracted list
    extracted_map: Dict[str, Dict] = {e["nutrient"]: e for e in extracted_nutrients}

    scored_nutrients = []
    condition_warnings = []
    missing_nutrients = []
    total_weight = 0.0
    weighted_score_sum = 0.0

    for nutrient_name, profile in _PROFILES.items():
        if nutrient_name not in extracted_map:
            missing_nutrients.append(nutrient_name)
            continue

        entry = extracted_map[nutrient_name]
        value = float(entry["value"])
        raw_score = _score_single(value, profile)
        weight = profile["weight"]

        weighted_score_sum += raw_score * weight
        total_weight += weight

        scored_nutrients.append({
            "nutrient": nutrient_name,
            "value": value,
            "unit": entry["unit"],
            "score": raw_score,
            "weight": weight,
            "direction": profile["direction"],
        })

        warnings = _check_condition_warnings(nutrient_name, value, user_conditions)
        condition_warnings.extend(warnings)

    final_score = round(weighted_score_sum / total_weight, 2) if total_weight > 0 else None

    return {
        "score": final_score,
        "scored_nutrients": scored_nutrients,
        "condition_warnings": condition_warnings,
        "missing_nutrients": missing_nutrients,
    }
