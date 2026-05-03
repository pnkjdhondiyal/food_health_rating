import os
import uuid
from functools import wraps
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from advisory.recommender import generate_health_advice
from database import (
    create_scan_record,
    create_user,
    get_scan_record,
    get_user_by_email,
    get_user_by_id,
    init_db,
    list_scan_records,
    update_user_conditions,
)
from nlp.parser import extract_ingredients
from ocr.ocr_engine import extract_text
from scoring.scorer import calculate_health_rating


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
        advice_result["personalized_advice"] = "Log in and set your health profile to save this scan and get personalized warnings."
        advice_result["profile_recommendations"] = []
        return advice_result

    user_conditions = {condition.lower() for condition in user.get("health_conditions", [])}
    profile_recommendations = [
        recommendation
        for recommendation in advice_result["recommendations"]
        if recommendation["condition"].lower() in user_conditions
    ]

    if not user_conditions:
        personalized_advice = "Add health conditions to your profile for personalized warnings."
    elif profile_recommendations:
        condition_names = ", ".join(recommendation["condition"] for recommendation in profile_recommendations)
        personalized_advice = f"Personal warning for your profile: review the {condition_names} recommendation before eating this."
    else:
        personalized_advice = "No strong warning matched your saved health profile from the current dataset."

    advice_result["personalized_advice"] = personalized_advice
    advice_result["profile_recommendations"] = profile_recommendations
    return advice_result


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


@app.route("/analyze", methods=["POST"])
def analyze():
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
        ingredients = extract_ingredients(ocr_text)
        score_result = calculate_health_rating(ingredients)
        advice_result = generate_health_advice(score_result["matched_ingredients"])
        advice_result = personalize_advice(advice_result, current_user())

        result = {
            "text": ocr_text,
            "ingredients": ingredients,
            "matched": score_result["matched_ingredients"],
            "score": score_result["score"],
            "rating": score_result["rating_label"],
            "star_count": score_result["star_count"],
            "classification": score_result["classification"],
            "advice": advice_result["advice"],
            "personalized_advice": advice_result["personalized_advice"],
            "better_options": advice_result["better_options"],
            "recommendations": advice_result["recommendations"],
            "profile_recommendations": advice_result["profile_recommendations"],
            "saved": False,
        }

        user = current_user()
        if user:
            scan_id = create_scan_record(user["id"], product_name, unique_name, result)
            result["saved"] = True
            result["scan_id"] = scan_id

        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": f"Unable to process the image: {exc}"}), 500


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(debug=True)
