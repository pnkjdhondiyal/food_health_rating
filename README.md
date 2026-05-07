# 🍎 Food Health Rating System (India Focused)

## 📌 Overview

The Food Health Rating System is an AI-based application designed to analyze packaged food products and provide a simplified health rating based on their ingredients.

In India, most consumers find it difficult to interpret complex ingredient labels (e.g., preservatives, E-codes, additives). This project bridges that gap by converting raw ingredient data into an easy-to-understand health score and explanation.

---

## 🎯 Problem Statement

* Food labels are difficult to understand for common users
* Harmful ingredients like added sugar, palm oil, and preservatives are often ignored
* No simple system exists in India to rate packaged food healthiness

---

## 💡 Solution

This system allows users to:

1. Upload an image of a packaged food label
2. Extract ingredients using OCR
3. Analyze ingredients using a custom health scoring system
4. Generate a health rating (⭐ scale)
5. Provide explanations for detected harmful ingredients

---

## 🚀 Key Features

* 📸 Image Upload Interface
* 🔍 OCR-based Ingredient Extraction
* 🧠 Ingredient Classification (Healthy / Moderate / Harmful)
* ⭐ Health Rating System (1–5 scale)
* ⚠️ Ingredient Warnings (e.g., high sugar, processed oils)
* 📊 (Future) Dashboard for tracking food health history

---

## 🧠 System Architecture

User Input → Image Upload → OCR → Text Cleaning → Ingredient Extraction → Scoring Engine → Health Rating Output

---

## 🛠 Tech Stack

* **Frontend**: Streamlit / React
* **Backend**: Flask
* **OCR**: Tesseract OCR
* **NLP**: spaCy / Text Processing
* **ML (Optional)**: Scikit-learn
* **Database (Future)**: Firebase / JSON

---

## ⚙️ Working Pipeline

1. User uploads food label image
2. OCR extracts raw text
3. Text is cleaned and normalized
4. Ingredients are matched with a predefined dataset
5. Each ingredient is assigned a health score
6. Weighted scoring is applied
7. Final rating is generated

---

## 📊 Scoring Logic (Basic Idea)

* Harmful ingredients → Negative score
* Healthy ingredients → Positive score
* Ingredient order → Used as weight

Example:

* Sugar → -5
* Palm Oil → -3
* Whole Wheat → +4

Final Score = Weighted sum of ingredient scores

---

## ⚠️ Challenges

* OCR inaccuracies (noisy text, blurry images)
* Multiple naming formats (e.g., sucrose = sugar)
* Lack of structured datasets for Indian products
* Missing quantity percentages in labels

---

## 🔮 Future Enhancements

* 📦 Barcode scanning for instant product lookup
* 📊 Dashboard with health trends
* 🤖 ML-based food classification
* 👤 Personalized recommendations (diabetic, weight loss, etc.)
* 🌍 Integration with global food datasets

---

## 📈 Impact

* Helps users make informed food choices
* Increases awareness about harmful ingredients
* Bridges the gap between raw labels and understanding
* Potential to scale into a real-world consumer application

---

## 👩‍💻 Author

**Gitanjali Pandey**
B.Tech CSE | Aspiring Software Developer

---

## ⭐ Acknowledgement

Inspired by global systems like health rating models used in other countries, adapted for Indian consumer needs.
