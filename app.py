import os
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from advisory.recommender import generate_health_advice
from nlp.parser import extract_ingredients
from ocr.ocr_engine import extract_text
from scoring.scorer import calculate_health_rating


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff"}


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/how-it-works", methods=["GET"])
def how_it_works():
    return render_template("howitworks.html")


@app.route("/results", methods=["GET"])
def results():
    return render_template("results.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    uploaded_file = request.files.get("image")

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

        return jsonify(
            {
                "text": ocr_text,
                "ingredients": ingredients,
                "matched": score_result["matched_ingredients"],
                "score": score_result["score"],
                "rating": score_result["rating_label"],
                "star_count": score_result["star_count"],
                "classification": score_result["classification"],
                "advice": advice_result["advice"],
                "better_options": advice_result["better_options"],
                "recommendations": advice_result["recommendations"],
            }
        )
    except Exception as exc:
        return jsonify({"error": f"Unable to process the image: {exc}"}), 500


if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.run(debug=True)
