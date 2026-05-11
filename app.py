import os
import uuid
from datetime import date
from functools import wraps
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from advisory.recommender import generate_health_advice
from advisory.snack_recommender import recommend_better_snacks
from database import (
    create_scan_record,
    create_user,
    get_daily_totals,
    get_logged_dates,
    get_nutrient_log_by_date,
    get_scan_record,
    get_user_by_email,
    get_user_by_id,
    init_db,
    list_scan_records,
    log_nutrients,
    update_user_conditions,
)
from nlp.nutrient_parser import extract_nutrients
from nlp.parser import extract_ingredients
from ocr.ocr_engine import extract_text
from scoring.nutrient_scorer import calculate_nutrient_score
from scoring.scorer import calculate_health_rating, combine_scores, get_classification, get_rating, get_rating_label


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff"}
HEALTH_CONDITIONS = [
    "diabetes",
    "hypertension",
    "heart disease",
    "kidney disease",
    "celiac disease",
    "lactose intolerance",
]


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-before-production")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
init_db()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(int(user_id))


@app.context_processor
def inject_user():
    return {"current_user": current_user(), "health_conditions": HEALTH_CONDITIONS}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if current_user() is None:
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def selected_conditions_from_form() -> list[str]:
    selected = request.form.getlist("health_conditions")
    return [condition for condition in selected if condition in HEALTH_CONDITIONS]


def personalize_advice(advice_result: dict, user: dict | None) -> dict:
    if not user:
        advice_result["personalized_advice"] = "Log in for personal recommendations."
        advice_result["recommendation_status"] = "neutral"
        advice_result["profile_recommendations"] = []
        return advice_result

    user_conditions = {condition.lower() for condition in user.get("health_conditions", [])}
    profile_recommendations = [
        recommendation
        for recommendation in advice_result["recommendations"]
        if recommendation["condition"].lower() in user_conditions
    ]

    if not user_conditions:
        personalized_advice = "Add health conditions to get personal recommendations."
        recommendation_status = "neutral"
    elif profile_recommendations:
        condition_names = ", ".join(recommendation["condition"] for recommendation in profile_recommendations)
        personalized_advice = f"Warning for you: review the {condition_names} recommendation before eating this."
        recommendation_status = "warning"
    else:
        personalized_advice = "No strong warning for you."
        recommendation_status = "safe"

    advice_result["personalized_advice"] = personalized_advice
    advice_result["recommendation_status"] = recommendation_status
    advice_result["profile_recommendations"] = profile_recommendations
    return advice_result


def get_important_ingredients(matched_ingredients: list[dict]) -> dict[str, list[dict]]:
    important = {"hazards": [], "good": []}

    for item in matched_ingredients:
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

    important["hazards"] = important["hazards"][:6]
    important["good"] = important["good"][:6]
    return important


def delete_uploaded_file(path: Path) -> None:
    try:
        if path.exists() and path.is_file():
            path.unlink()
    except OSError:
        app.logger.warning("Could not delete uploaded file: %s", path)


def cleanup_upload_folder() -> None:
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    for path in UPLOAD_FOLDER.iterdir():
        if path.is_file():
            delete_uploaded_file(path)


cleanup_upload_folder()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/how-it-works", methods=["GET"])
def how_it_works():
    return render_template("howitworks.html")


@app.route("/results", methods=["GET"])
def results():
    return render_template("results.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        health_conditions = selected_conditions_from_form()

        if not name or not email or not password:
            flash("Name, email, and password are required.")
            return render_template("signup.html", selected_conditions=health_conditions)

        if get_user_by_email(email):
            flash("An account with this email already exists.")
            return render_template("signup.html", selected_conditions=health_conditions)

        create_user(name, email, generate_password_hash(password), health_conditions)
        flash("Account created. Please log in to open your dashboard.")
        return redirect(url_for("login"))

    return render_template("signup.html", selected_conditions=[])


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_user_by_email(email)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.")
            return render_template("login.html", email=email)

        session["user_id"] = user["id"]
        flash("Welcome back.")
        return redirect(url_for("dashboard"))

    return render_template("login.html", email="")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    user = current_user()
    records = list_scan_records(user["id"])
    return render_template("dashboard.html", user=user, records=records[:3], scan_count=len(records))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        health_conditions = selected_conditions_from_form()
        update_user_conditions(user["id"], health_conditions)
        flash("Health profile updated.")
        return redirect(url_for("profile"))

    return render_template("profile.html", user=user, selected_conditions=user["health_conditions"])


@app.route("/history", methods=["GET"])
@login_required
def history():
    records = list_scan_records(current_user()["id"])
    return render_template("history.html", records=records)


@app.route("/history/<int:scan_id>", methods=["GET"])
@login_required
def history_detail(scan_id: int):
    record = get_scan_record(current_user()["id"], scan_id)
    if record is None:
        flash("Scan record not found.")
        return redirect(url_for("history"))
    return render_template("scan_detail.html", record=record, result=record["result"])


@app.route("/scan/<int:scan_id>", methods=["GET"])
@login_required
def scan_result(scan_id: int):
    return history_detail(scan_id)


@app.route("/analyze", methods=["POST"])
def analyze():
    user = current_user()
    if user is None:
        return jsonify({"error": "Please sign in and create your health profile before analyzing food."}), 401

    if not user.get("health_conditions"):
        return jsonify({"error": "Please complete your health profile before analyzing food."}), 403

    uploaded_file = request.files.get("image")
    product_name = request.form.get("product_name", "").strip()

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "Please select an image file to upload."}), 400

    if not allowed_file(uploaded_file.filename):
        return jsonify({"error": "Unsupported file type. Upload PNG, JPG, JPEG, BMP, or TIFF."}), 400

    filename = secure_filename(uploaded_file.filename)
    unique_name = f"{Path(filename).stem}_{uuid.uuid4().hex[:8]}{Path(filename).suffix}"
    save_path = UPLOAD_FOLDER / unique_name
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    uploaded_file.save(save_path)

    try:
        ocr_text = extract_text(str(save_path))
        user_conditions = user.get("health_conditions", [])

        ingredients = extract_ingredients(ocr_text)
        score_result = calculate_health_rating(ingredients)

        extracted_nutrients = extract_nutrients(ocr_text)
        nutrient_result = calculate_nutrient_score(extracted_nutrients, user_conditions)

        final_score = combine_scores(score_result["score"], nutrient_result["score"])
        final_star_count = get_rating(final_score) if final_score is not None else 0
        final_classification = get_classification(final_score)
        final_rating_label = get_rating_label(final_score)

        advice_result = generate_health_advice(score_result["matched_ingredients"])
        advice_result = personalize_advice(advice_result, user)
        important_ingredients = get_important_ingredients(score_result["matched_ingredients"])
        snack_recommendations = recommend_better_snacks(
            user_conditions,
            advice_result["profile_recommendations"] or advice_result["recommendations"],
        )

        result = {
            "text": ocr_text,
            "ingredients": ingredients,
            "matched": score_result["matched_ingredients"],
            "ingredient_score": score_result["score"],
            "nutrient_score": nutrient_result["score"],
            "scored_nutrients": nutrient_result["scored_nutrients"],
            "nutrient_condition_warnings": nutrient_result["condition_warnings"],
            "score": final_score,
            "rating": final_rating_label,
            "star_count": final_star_count,
            "classification": final_classification,
            "advice": advice_result["advice"],
            "personalized_advice": advice_result["personalized_advice"],
            "recommendation_status": advice_result["recommendation_status"],
            "better_options": advice_result["better_options"],
            "recommendations": advice_result["recommendations"],
            "profile_recommendations": advice_result["profile_recommendations"],
            "important_ingredients": important_ingredients,
            "snack_recommendations": snack_recommendations,
            "saved": False,
        }

        scan_id = create_scan_record(user["id"], product_name, unique_name, result)
        result["saved"] = True
        result["scan_id"] = scan_id

        if nutrient_result["scored_nutrients"]:
            log_nutrients(
                user["id"],
                scan_id,
                product_name or unique_name,
                nutrient_result["scored_nutrients"],
                date.today().isoformat(),
            )

        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Unable to process the image: {exc}"}), 500
    finally:
        delete_uploaded_file(save_path)


@app.route("/nutrient-log", methods=["GET"])
@login_required
def nutrient_log():
    user = current_user()
    selected_date = request.args.get("date", date.today().isoformat())
    daily_totals = get_daily_totals(user["id"], selected_date)
    log_entries = get_nutrient_log_by_date(user["id"], selected_date)
    logged_dates = get_logged_dates(user["id"])
    daily_limits = _load_daily_limits(user.get("health_conditions", []))
    return render_template(
        "nutrient_log.html",
        user=user,
        selected_date=selected_date,
        daily_totals=daily_totals,
        log_entries=log_entries,
        logged_dates=logged_dates,
        daily_limits=daily_limits,
    )


def _load_daily_limits(user_conditions: list[str]) -> dict[str, dict]:
    """Return per-nutrient daily limits, using condition-specific limits where applicable."""
    import csv
    limits: dict[str, dict] = {}
    condition_set = {c.lower() for c in user_conditions}
    limits_path = BASE_DIR / "data" / "nutrient_limits.csv"
    with limits_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            nutrient = row["nutrient"].strip().lower()
            general_limit = float(row["daily_limit"]) if row["daily_limit"] else None
            condition = row.get("condition", "").strip().lower()
            condition_limit = float(row["condition_limit"]) if row.get("condition_limit") else None
            unit = row["unit"].strip()

            if nutrient not in limits:
                limits[nutrient] = {"limit": general_limit, "unit": unit}

            # Override with stricter condition limit if user has that condition
            if condition and condition in condition_set and condition_limit is not None:
                if condition_limit < (limits[nutrient]["limit"] or float("inf")):
                    limits[nutrient]["limit"] = condition_limit
    return limits


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(debug=True)
