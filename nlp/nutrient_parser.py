import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
NUTRIENT_PROFILES_PATH = BASE_DIR / "data" / "nutrient_profiles.csv"

# Matches the nutrition facts section in OCR text
NUTRITION_SECTION_PATTERN = re.compile(
    r"(?:nutrition(?:al)?\s*(?:information|facts|value|values|info)?)\s*[:\-]?\s*(.+?)(?=\b(?:ingredients?|allergen|storage|best before|manufactured)\b|$)",
    re.IGNORECASE | re.DOTALL,
)

# Matches a value+unit pair like "3.5g", "620mg", "450kcal", "2.1 g"
VALUE_UNIT_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(kcal|cal|mg|g|iu|mcg|µg|%)?",
    re.IGNORECASE,
)


def _load_alias_map() -> Dict[str, str]:
    """Build a flat alias -> canonical_nutrient_name lookup from the profiles CSV."""
    alias_map: Dict[str, str] = {}
    with NUTRIENT_PROFILES_PATH.open(mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = row["nutrient"].strip().lower()
            alias_map[canonical] = canonical
            for alias in row.get("aliases", "").split("|"):
                alias = alias.strip().lower()
                if alias:
                    alias_map[alias] = canonical
    return alias_map


# Load once at module level
_ALIAS_MAP: Dict[str, str] = _load_alias_map()


def _extract_nutrition_section(ocr_text: str) -> str:
    """Return the nutrition facts block from OCR text, or the full text as fallback."""
    match = NUTRITION_SECTION_PATTERN.search(ocr_text)
    return match.group(1).strip() if match else ocr_text


def _normalize_line(line: str) -> str:
    """Clean a single OCR line for parsing."""
    line = re.sub(r"\s+", " ", line)
    # Remove table separators and pipe characters
    line = re.sub(r"[|]{1,}", " ", line)
    return line.strip()


def _match_nutrient_name(text: str) -> Optional[str]:
    """Try to match a nutrient name from the alias map in the given text fragment."""
    text_lower = text.lower().strip()
    # Exact match first
    if text_lower in _ALIAS_MAP:
        return _ALIAS_MAP[text_lower]
    # Partial match — check if any alias is contained in the text
    for alias, canonical in _ALIAS_MAP.items():
        if alias in text_lower:
            return canonical
    return None


def _parse_value_unit(text: str) -> Optional[Tuple[float, str]]:
    """Extract the first numeric value and its unit from a text fragment."""
    match = VALUE_UNIT_PATTERN.search(text)
    if not match:
        return None
    value = float(match.group(1))
    unit = (match.group(2) or "g").lower()
    # Normalize unit aliases
    if unit in ("cal", "kcal"):
        unit = "kcal"
    elif unit in ("mcg", "µg"):
        unit = "mcg"
    return value, unit


def _parse_line(line: str) -> Optional[Dict[str, object]]:
    """
    Try to extract a nutrient entry from a single OCR line.
    Expected formats:
      - "Total Fat 18g"
      - "Sodium 620 mg"
      - "Energy 450kcal 90kcal"   (per 100g first, per serving second)
      - "Protein   12.5 g   2.5 g"
    Returns the per-100g value when two values are present.
    """
    line = _normalize_line(line)
    if not line:
        return None

    # Split line into text part and numeric parts
    # Find all value+unit occurrences
    value_matches = list(VALUE_UNIT_PATTERN.finditer(line))
    if not value_matches:
        return None

    # The nutrient name is everything before the first number
    first_match_start = value_matches[0].start()
    name_fragment = line[:first_match_start].strip()

    canonical = _match_nutrient_name(name_fragment)
    if canonical is None:
        return None

    # Use the first value (per 100g column on most Indian labels)
    value_unit = _parse_value_unit(value_matches[0].group(0))
    if value_unit is None:
        return None

    value, unit = value_unit
    return {"nutrient": canonical, "value": value, "unit": unit, "raw_line": line}


def extract_nutrients(ocr_text: str) -> List[Dict[str, object]]:
    """
    Extract nutrient name/value/unit triplets from OCR text.
    Returns a list of dicts: [{"nutrient": "sodium", "value": 620.0, "unit": "mg"}, ...]
    Deduplicates by nutrient name, keeping the first occurrence.
    """
    if not ocr_text:
        return []

    section = _extract_nutrition_section(ocr_text)
    lines = section.splitlines()

    seen: Dict[str, Dict[str, object]] = {}
    for line in lines:
        entry = _parse_line(line)
        if entry and entry["nutrient"] not in seen:
            seen[entry["nutrient"]] = entry

    return list(seen.values())
