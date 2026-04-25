import csv
import re
from pathlib import Path
from statistics import mean
from typing import Dict, List

from rapidfuzz import fuzz, process


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "data" / "ingredients.csv"
MATCH_THRESHOLD = 75
RAW_SCORE_MIN = -4
RAW_SCORE_MAX = 5


def normalize_ingredient_name(value: str) -> str:
    """Reduce OCR noise before fuzzy matching."""
    value = value.lower()
    value = re.sub(r"\(\s*\d+(?:\.\d+)?\s*%?\s*\)", " ", value)
    value = re.sub(r"\b\d+(?:\.\d+)?\s*%\b", " ", value)
    value = re.sub(r"[^a-z0-9\s&-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_score(raw_score: float) -> float:
    """Map internal ingredient scores from -4..5 to a user-facing 0..5 scale."""
    clipped_score = max(RAW_SCORE_MIN, min(RAW_SCORE_MAX, raw_score))
    normalized = ((clipped_score - RAW_SCORE_MIN) / (RAW_SCORE_MAX - RAW_SCORE_MIN)) * 5
    return round(normalized, 2)


def parse_caution_conditions(value: str) -> List[str]:
    if not value:
        return []
    return [condition.strip() for condition in value.split("|") if condition.strip()]


def load_ingredient_dataset() -> Dict[str, Dict[str, object]]:
    """Load ingredient scores and condition cautions from the CSV dataset."""
    dataset: Dict[str, Dict[str, object]] = {}
    with DATASET_PATH.open(mode="r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            ingredient = row["ingredient"].strip().lower()
            dataset[ingredient] = {
                "health_score": float(row["health_score"]),
                "caution_conditions": parse_caution_conditions(row.get("caution_conditions", "")),
            }
    return dataset


def get_rating(score: float) -> int:
    if score >= 4:
        return 5
    if score >= 3:
        return 4
    if score >= 2:
        return 3
    if score >= 1:
        return 2
    return 1


def get_rating_label(score: float | None) -> str:
    if score is None:
        return "Insufficient data"
    return f"{get_rating(score)} stars"


def get_classification(score: float | None) -> str:
    if score is None:
        return "Moderate"
    if score >= 3.5:
        return "Healthy"
    if score >= 2:
        return "Moderate"
    return "Unhealthy"


def calculate_health_rating(ingredients: List[str]) -> Dict[str, object]:
    """Fuzzy match OCR ingredients to the dataset and compute the average score."""
    ingredient_dataset = load_ingredient_dataset()
    dataset_ingredients = list(ingredient_dataset.keys())
    normalized_lookup = {normalize_ingredient_name(name): name for name in dataset_ingredients}
    normalized_dataset = list(normalized_lookup.keys())
    matched_ingredients = []
    matched_scores = []

    for ingredient in ingredients:
        normalized_ingredient = normalize_ingredient_name(ingredient)
        if not normalized_ingredient:
            continue

        if normalized_ingredient in normalized_lookup:
            matched_name = normalized_lookup[normalized_ingredient]
            ingredient_info = ingredient_dataset[matched_name]
            raw_score = ingredient_info["health_score"]
            score = normalize_score(raw_score)
            matched_ingredients.append(
                {
                    "ocr_ingredient": ingredient,
                    "matched_ingredient": matched_name,
                    "match_score": 100.0,
                    "health_score": score,
                    "caution_conditions": ingredient_info["caution_conditions"],
                }
            )
            matched_scores.append(score)
            continue

        match = process.extractOne(normalized_ingredient, normalized_dataset, scorer=fuzz.WRatio)
        if match and match[1] >= MATCH_THRESHOLD:
            matched_name = normalized_lookup[match[0]]
            ingredient_info = ingredient_dataset[matched_name]
            raw_score = ingredient_info["health_score"]
            score = normalize_score(raw_score)
            matched_ingredients.append(
                {
                    "ocr_ingredient": ingredient,
                    "matched_ingredient": matched_name,
                    "match_score": round(match[1], 2),
                    "health_score": score,
                    "caution_conditions": ingredient_info["caution_conditions"],
                }
            )
            matched_scores.append(score)
        else:
            matched_ingredients.append(
                {
                    "ocr_ingredient": ingredient,
                    "matched_ingredient": "No good match found",
                    "match_score": 0,
                    "health_score": 0,
                    "caution_conditions": [],
                }
            )

    if matched_scores:
        average_score = round(mean(matched_scores), 2)
        star_count = get_rating(average_score)
    else:
        average_score = None
        star_count = 0

    return {
        "score": average_score,
        "rating": get_rating_label(average_score),
        "rating_label": get_rating_label(average_score),
        "star_count": star_count,
        "classification": get_classification(average_score),
        "matched_ingredients": matched_ingredients,
    }
