from typing import Dict, List


ILLNESS_RULES = {
    "diabetes": {
        "display_name": "Diabetes",
        "risk_keywords": {
            "sugar",
            "brown sugar",
            "cane sugar",
            "icing sugar",
            "castor sugar",
            "liquid sugar",
            "glucose",
            "glucose syrup",
            "liquid glucose",
            "liquid glucose syrup",
            "corn syrup",
            "high fructose corn syrup",
            "dextrose",
            "maltodextrin",
            "fructose",
            "invert syrup",
            "invert sugar syrup",
            "jaggery",
            "honey",
            "molasses",
            "sweetened condensed milk",
        },
        "advice": "This product includes sugars or syrups that may raise blood glucose quickly.",
        "better_options": [
            "Choose unsweetened oats, roasted chana, or plain makhana.",
            "Prefer products with whole grains and no added sugar near the top of the ingredient list.",
            "Pick snacks with shorter ingredient lists and fewer sweeteners.",
        ],
    },
    "hypertension": {
        "display_name": "Hypertension",
        "risk_keywords": {
            "salt",
            "sea salt",
            "iodized salt",
            "rock salt",
            "black salt",
            "sodium",
            "sodium benzoate",
            "baking soda",
            "raising agent",
            "raising agents",
            "500 i",
            "500 ii",
            "500(ii)",
        },
        "advice": "This product contains salt or sodium-based additives that may not be ideal for someone managing blood pressure.",
        "better_options": [
            "Choose low-sodium roasted nuts, seeds, or plain khakhra.",
            "Look for products where salt appears lower in the ingredient list.",
            "Prefer minimally processed snacks over strongly flavored packaged foods.",
        ],
    },
    "heart disease": {
        "display_name": "Heart Disease",
        "risk_keywords": {
            "palm oil",
            "refined palm oil",
            "vegetable oil",
            "soybean oil",
            "cottonseed oil",
            "butter",
            "cream",
            "cheese",
            "vanaspati",
            "hydrogenated vegetable fat",
        },
        "advice": "The product contains refined fats or saturated-fat-heavy ingredients that are better limited for heart health.",
        "better_options": [
            "Choose snacks based on oats, millets, nuts, or seeds.",
            "Prefer labels using rice bran oil, mustard oil, or olive oil instead of palm oil.",
            "Look for baked whole-grain options with fewer fat-based additives.",
        ],
    },
    "kidney disease": {
        "display_name": "Kidney Disease",
        "risk_keywords": {
            "salt",
            "sea salt",
            "iodized salt",
            "potassium iodate",
            "potassium sorbate",
            "potassium metabisulphite",
            "potassium metabisulfite",
            "sodium",
        },
        "advice": "The product may contain sodium or potassium additives that some kidney patients are advised to monitor closely.",
        "better_options": [
            "Prefer simple homemade snacks with limited salt and fewer additives.",
            "Choose plain poha, unsalted seeds, or roasted chana if they fit your diet plan.",
            "Check with a clinician if potassium or sodium restriction applies to you.",
        ],
    },
    "celiac disease": {
        "display_name": "Celiac Disease",
        "risk_keywords": {
            "wheat",
            "wheat flour",
            "refined wheat flour",
            "refined wheat flour maida",
            "maida",
            "atta",
            "semolina",
            "suji",
            "barley",
            "rye",
            "bread crumbs",
        },
        "advice": "This product appears to contain gluten-based grains and may not be suitable for someone with celiac disease.",
        "better_options": [
            "Choose certified gluten-free options made with rice, jowar, bajra, or makhana.",
            "Prefer products based on millet flour, corn, or quinoa.",
            "Always check for gluten cross-contamination warnings on packaged labels.",
        ],
    },
    "lactose intolerance": {
        "display_name": "Lactose Intolerance",
        "risk_keywords": {
            "milk",
            "milk solids",
            "milk solids nonfat",
            "nonfat milk solids",
            "whole milk powder",
            "skim milk powder",
            "skimmed milk powder",
            "milk powder",
            "curd",
            "yogurt",
            "cheese",
            "cream",
            "buttermilk powder",
            "whey protein",
            "casein",
            "milk protein concentrate",
            "sweetened condensed milk",
        },
        "advice": "This product includes dairy-derived ingredients that may trigger discomfort for someone with lactose intolerance.",
        "better_options": [
            "Look for dairy-free snacks made with oats, millet, nuts, or coconut.",
            "Choose labels without milk solids, whey, casein, or cream.",
            "Prefer roasted chana, seed mixes, or dairy-free nut bars.",
        ],
    },
}


def generate_health_advice(matched_ingredients: List[Dict[str, object]]) -> Dict[str, object]:
    recommendations = []
    all_better_options = []

    for rule in ILLNESS_RULES.values():
        risk_flags = []
        for item in matched_ingredients:
            matched_name = str(item.get("matched_ingredient", "")).lower()
            if matched_name in rule["risk_keywords"]:
                risk_flags.append(matched_name)

        unique_flags = sorted(set(risk_flags))
        if not unique_flags:
            continue

        severity = "avoid" if len(unique_flags) >= 2 else "limit"
        message = (
            f"If you have {rule['display_name']}, "
            f"{'it may be better to avoid this product' if severity == 'avoid' else 'consume this in limited quantity'} "
            f"because it contains: {', '.join(unique_flags)}."
        )
        recommendations.append(
            {
                "condition": rule["display_name"],
                "severity": severity,
                "message": message,
                "risk_flags": unique_flags,
            }
        )
        all_better_options.extend(rule["better_options"])

    if not recommendations:
        return {
            "advice": "General guidance: this product does not strongly trigger the current illness rules, but refined and additive-heavy foods are still best eaten occasionally.",
            "better_options": [
                "Prefer whole grains, pulses, nuts, seeds, and shorter ingredient lists.",
                "Choose products with less added sugar and fewer artificial additives.",
                "Homemade or minimally processed snacks are often better options.",
            ],
            "recommendations": [],
        }

    deduped_options = list(dict.fromkeys(all_better_options))
    return {
        "advice": "Automatic recommendation: this product may not be ideal for some people with specific health conditions.",
        "better_options": deduped_options[:6],
        "recommendations": recommendations,
    }
