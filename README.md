# Food Health Rating System

## Overview

Food Health Rating System is a Flask-based web application that helps users understand packaged food labels. The app uses OCR to read an uploaded ingredient-label image, extracts ingredients, matches them against a health-scored dataset, generates a rating, highlights risky and healthy ingredients, and gives personalized recommendations based on the user's health profile.

The project is focused on practical food-label understanding for Indian packaged foods, where ingredients may include sugar aliases, E-numbers, preservatives, refined oils, milk solids, gluten sources, sodium additives, and other terms that are difficult for normal users to interpret.

## Main Goal

The goal is not only to scan a label once. The app is designed as a personal food health assistant:

- Users create an account.
- Users select health conditions such as diabetes or hypertension.
- Users scan packaged food labels.
- The app gives condition-based warnings.
- The result is saved to the user's history.
- The user can revisit past scans without scanning the same product again.
- The app suggests better snack alternatives.

## Current Features

### User Accounts

The app supports sign up, sign in, logout, and profile management.

User data is stored in a local SQLite database. Passwords are not stored as plain text; they are hashed using Werkzeug password hashing.

Files involved:

- `app.py`
- `database.py`
- `templates/signup.html`
- `templates/login.html`
- `templates/profile.html`

### Health Profile

Before scanning food, the user must complete a health profile. The current supported health conditions are:

- Diabetes
- Hypertension
- Heart disease
- Kidney disease
- Celiac disease
- Lactose intolerance

This profile is used to personalize warnings. For example, if a user has diabetes and a scanned product contains sugar, glucose syrup, maltodextrin, or similar ingredients, the app warns the user before eating it.

### Scan Requirement

Users cannot analyze food without creating and completing a profile. This is enforced in two places:

- The homepage hides the scanner and asks users to create or complete a profile.
- The `/analyze` backend route rejects scan requests if the user is not logged in or has no selected health conditions.

This keeps every analysis personalized.

### Image Upload And OCR

Users upload a packaged food ingredient-label image. The app:

1. Saves the image temporarily.
2. Preprocesses it with OpenCV.
3. Extracts text using Tesseract OCR.
4. Deletes the uploaded image after analysis.

Files involved:

- `ocr/ocr_engine.py`
- `app.py`

Supported file types:

- PNG
- JPG
- JPEG
- BMP
- TIFF

Maximum upload size:

- 10 MB

### Automatic Upload Cleanup

Uploaded screenshots/images are not meant to stay in the project forever.

The app now deletes uploaded files automatically:

- On app startup, files inside `uploads/` are cleared.
- After each scan, the uploaded image is deleted in a `finally` block.

This protects user privacy and prevents the `uploads/` folder from filling up.

### Ingredient Extraction

OCR output can be noisy, so the app cleans and parses the extracted text.

The parser tries to:

- Find the ingredient section.
- Remove noisy heading fragments.
- Remove percentages.
- Split ingredients by commas, semicolons, and connector words.
- Normalize ingredient names for matching.

File involved:

- `nlp/parser.py`

### Ingredient Scoring

The app uses a CSV dataset of ingredients and health scores.

Dataset:

- `data/ingredients.csv`

Each ingredient has:

- `ingredient`
- `health_score`
- `caution_conditions`

Example caution conditions:

- diabetes
- hypertension
- kidney disease
- celiac disease
- lactose intolerance

The scoring engine:

1. Loads the ingredient dataset.
2. Normalizes OCR ingredients.
3. Matches OCR ingredients against dataset ingredients.
4. Uses exact matching first.
5. Uses RapidFuzz fuzzy matching if exact matching fails.
6. Converts raw ingredient scores to a 0-5 user-facing scale.
7. Calculates the average score.
8. Converts the score into stars and a classification.

File involved:

- `scoring/scorer.py`

Current classifications:

- Healthy
- Moderate
- Unhealthy

### Important Ingredients

The scan result page highlights important ingredients in two groups:

- Hazard Ingredients
- Good Ingredients

Hazard ingredients are ingredients that have low health scores or condition-specific cautions.

Good ingredients are ingredients with higher health scores, such as fiber-rich or whole-food ingredients.

This makes the result easier to understand than showing a long raw OCR list.

### Condition-Based Advice

The app has rule-based health advice for common conditions.

File involved:

- `advisory/recommender.py`

Example:

If the product contains sugar-related ingredients and the user has diabetes, the app may show:

```text
Warning for you: review the Diabetes recommendation before eating this.
```

If there is no strong profile-specific warning:

```text
No strong warning for you.
```

### Better Snack Recommendations

The app recommends better snack options based on the user's health profile and the warnings triggered by the scan.

Files involved:

- `advisory/snack_recommender.py`
- `data/snack_recommendations.csv`

Example snacks:

- Roasted chana
- Plain makhana
- Unsalted peanuts
- Sprout chaat
- Vegetable sticks with hummus
- Plain oats
- Air-popped popcorn

The recommendation dataset contains:

- `snack_name`
- `good_for`
- `avoid_for`
- `reason`
- `tags`

The snack recommender avoids snacks that conflict with the user's health profile. For example, if the user has kidney disease, snacks marked as `avoid_for` kidney disease are skipped.

### Scan History

When a logged-in user scans a product, the result is saved in SQLite.

Saved data includes:

- Product name
- OCR text
- Extracted ingredients
- Matched ingredients
- Score
- Rating
- Classification
- Personalized advice
- Important ingredients
- Snack recommendations
- Timestamp

Pages involved:

- `templates/history.html`
- `templates/scan_detail.html`

This allows users to open old reports without scanning again.

### Dashboard

The dashboard gives the user a quick overview of:

- Health conditions
- Saved scan count
- Latest activity
- Recent scan results
- Top better snack suggestion for recent scans

File involved:

- `templates/dashboard.html`

## Application Flow

### New User Flow

1. User opens the app.
2. User signs up.
3. User logs in.
4. User selects health conditions in the profile.
5. User scans a food label.
6. App shows the scan report.
7. App saves the scan to history.
8. User can revisit the report later.

### Scan Flow

```text
Image upload
-> OCR preprocessing
-> Tesseract text extraction
-> Ingredient parsing
-> Ingredient matching
-> Score calculation
-> Health classification
-> Condition-based advice
-> Better snack recommendation
-> Save scan history
-> Show scan result page
```

## Project Structure

```text
food-health-app/
├── app.py
├── database.py
├── requirements.txt
├── README.md
├── advisory/
│   ├── recommender.py
│   └── snack_recommender.py
├── data/
│   ├── ingredients.csv
│   └── snack_recommendations.csv
├── nlp/
│   └── parser.py
├── ocr/
│   └── ocr_engine.py
├── scoring/
│   └── scorer.py
├── static/
│   ├── script.js
│   ├── results.js
│   └── style.css
├── templates/
│   ├── index.html
│   ├── howitworks.html
│   ├── signup.html
│   ├── login.html
│   ├── profile.html
│   ├── dashboard.html
│   ├── history.html
│   ├── results.html
│   └── scan_detail.html
└── uploads/
```

## Important Files Explained

### `app.py`

Main Flask application.

Responsibilities:

- Defines routes.
- Handles signup/login/logout.
- Enforces login/profile before scanning.
- Accepts image uploads.
- Calls OCR, parser, scorer, advice engine, and snack recommender.
- Saves scan records.
- Deletes temporary uploaded images.

Important routes:

- `/`
- `/how-it-works`
- `/signup`
- `/login`
- `/logout`
- `/profile`
- `/dashboard`
- `/history`
- `/history/<scan_id>`
- `/scan/<scan_id>`
- `/analyze`

### `database.py`

SQLite database helper.

Responsibilities:

- Creates tables.
- Adds users.
- Updates health conditions.
- Saves scan records.
- Loads scan history.
- Adds fallback support for older scan records.

Tables:

- `users`
- `scan_records`

### `ocr/ocr_engine.py`

Handles image preprocessing and OCR.

Uses:

- OpenCV
- pytesseract

Steps:

- Read image.
- Convert to grayscale.
- Resize image.
- Blur image.
- Apply adaptive thresholding.
- Run Tesseract OCR.

### `nlp/parser.py`

Extracts ingredient names from OCR text.

It cleans OCR text and returns a list of normalized ingredients.

### `scoring/scorer.py`

Matches extracted ingredients to the dataset and calculates rating.

Uses:

- CSV dataset
- RapidFuzz fuzzy matching
- Score normalization

### `advisory/recommender.py`

Generates condition-based warnings.

Example conditions:

- Diabetes
- Hypertension
- Heart disease
- Kidney disease
- Celiac disease
- Lactose intolerance

### `advisory/snack_recommender.py`

Generates better snack suggestions based on:

- User health profile
- Triggered scan warnings
- Snack recommendation dataset

### `data/ingredients.csv`

Ingredient dataset used for scoring and condition warnings.

### `data/snack_recommendations.csv`

Snack recommendation dataset used for better snack suggestions.

### `static/script.js`

Handles the homepage analyzer:

- File selection
- Drag and drop
- Upload request to `/analyze`
- Redirect to scan result page

### `static/results.js`

Renders scan results for session-based result display.

### `static/style.css`

Shared styling for the web app.

## Setup Instructions

### 1. Install Python

Use Python 3.10 or newer.

### 2. Install Tesseract OCR

This project requires the Tesseract OCR engine.

On Windows, install it to the default location if possible:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

The app checks that common Windows path automatically.

### 3. Create a virtual environment

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\activate
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Run the app

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Dependencies

From `requirements.txt`:

```text
Flask
Werkzeug
opencv-python
pytesseract
rapidfuzz
```

External system dependency:

```text
Tesseract OCR
```

## Database

The app uses SQLite:

```text
food_health.sqlite3
```

This file stores users and scan history.

It should not be committed to Git because it contains local user data.

## Privacy Notes

Uploaded food-label images are temporary.

The app deletes uploaded files:

- when the app starts
- after every scan attempt

The saved scan history stores analysis data, not the uploaded image itself.

## Limitations

The project still has some practical limitations:

- OCR quality depends on image clarity.
- Nutrition quantities such as sugar grams are not fully parsed yet.
- The rating depends on the quality of the ingredient dataset.
- Fuzzy matching can sometimes map OCR text incorrectly.
- The health recommendations are rule-based, not medical diagnosis.

## Future Improvements

Possible next improvements:

- Nutrition facts image upload.
- Sugar, sodium, fat, fiber, and protein quantity extraction.
- Barcode scanning.
- Product search to avoid repeat scans.
- More Indian packaged food ingredients.
- More snack alternatives.
- Doctor/medical disclaimer section.
- Admin panel for editing ingredient and snack datasets.
- Unit tests for parser, scorer, recommender, and routes.

## Medical Disclaimer

This app is for educational and awareness purposes only. It is not medical advice. Users with medical conditions should follow professional medical guidance before changing their diet.

## Author

Food Health Rating System project.
