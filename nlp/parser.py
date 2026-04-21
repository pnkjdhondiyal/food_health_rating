import re
from typing import List


INGREDIENT_PATTERN = re.compile(
    r"(?:ingredients?|ingredient)\s*[:\-]?\s*(.+?)(?=\b(?:allergen|allergens|nutrition|nutritional|serving suggestion|storage instructions)\b|$)",
    re.IGNORECASE | re.DOTALL,
)


def extract_ingredients(ocr_text: str) -> List[str]:
    """Extract and normalize ingredients from OCR output."""
    if not ocr_text:
        return []

    match = INGREDIENT_PATTERN.search(ocr_text)
    if match:
        ingredient_text = match.group(1)
    else:
        # Fallback to the whole OCR text if no explicit ingredients label is found.
        ingredient_text = ocr_text

    # OCR often leaves a noisy heading fragment like "ingredients" or a misspelled variant.
    ingredient_text = re.sub(
        r"^\s*(?:ingredient\w*|ingredi\w*|ingre\w*|incre\w*)\s*[:\-]?\s*",
        "",
        ingredient_text,
        count=1,
        flags=re.IGNORECASE,
    )
    ingredient_text = re.sub(r"\s+", " ", ingredient_text)
    ingredient_text = re.sub(r"\(\s*\d+(?:\.\d+)?\s*%?\s*\)", " ", ingredient_text)
    ingredient_text = re.sub(r"\b\d+(?:\.\d+)?\s*%\b", " ", ingredient_text)
    ingredient_text = re.sub(r"\bcontains\b.*$", "", ingredient_text, flags=re.IGNORECASE)
    raw_ingredients = re.split(r",|;|\[[^\]]*\]", ingredient_text)

    cleaned_ingredients = []
    for item in raw_ingredients:
        normalized = re.sub(r"[^a-zA-Z0-9\s\-()&]", " ", item).strip().lower()
        normalized = re.sub(r"\s+", " ", normalized)
        if not normalized:
            continue

        parts = re.split(r"\s+(?:and|&)\s+", normalized)
        for part in parts:
            part = part.strip()
            if part:
                cleaned_ingredients.append(part)

    return cleaned_ingredients
