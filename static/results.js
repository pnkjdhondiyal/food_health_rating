const scoreValue = document.getElementById("score-value");
const starRating = document.getElementById("star-rating");
const ratingLabel = document.getElementById("rating-label");
const classificationBadge = document.getElementById("classification-badge");
const ingredientList = document.getElementById("ingredient-list");
const ocrText = document.getElementById("ocr-text");
const matchedTableBody = document.getElementById("matched-table-body");
const adviceText = document.getElementById("advice-text");
const personalizedAdvice = document.getElementById("personalized-advice");
const recommendationsList = document.getElementById("recommendations-list");
const betterOptions = document.getElementById("better-options");
const hazardIngredients = document.getElementById("hazard-ingredients");
const goodIngredients = document.getElementById("good-ingredients");

function classificationClass(value) {
    return String(value || "Moderate").toLowerCase().replace(/\s+/g, "-");
}

function renderStars(count) {
    const fullCount = Number.isFinite(count) ? count : 0;
    const filled = "\u2605".repeat(fullCount);
    const empty = "\u2606".repeat(Math.max(5 - fullCount, 0));
    starRating.textContent = filled + empty;
}

function renderPillList(container, items, emptyText) {
    container.innerHTML = "";
    if (!items.length) {
        const li = document.createElement("li");
        li.textContent = emptyText;
        container.appendChild(li);
        return;
    }
    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        container.appendChild(li);
    });
}

function renderAdviceList(items) {
    betterOptions.innerHTML = "";
    if (!items.length) {
        const li = document.createElement("li");
        li.textContent = "No alternative suggestions available.";
        betterOptions.appendChild(li);
        return;
    }
    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        betterOptions.appendChild(li);
    });
}

function renderImportantIngredients(container, items, emptyText, type) {
    if (!container) {
        return;
    }

    container.innerHTML = "";
    if (!items.length) {
        const li = document.createElement("li");
        li.className = "ingredient-chip neutral";
        li.textContent = emptyText;
        container.appendChild(li);
        return;
    }

    items.forEach((item) => {
        const li = document.createElement("li");
        li.className = `ingredient-chip ${type}`;
        const detail = item.cautions && item.cautions.length
            ? ` • ${item.cautions.join(", ")}`
            : ` • score ${item.score}`;
        li.textContent = `${item.name}${detail}`;
        container.appendChild(li);
    });
}

function renderRecommendationList(items) {
    recommendationsList.innerHTML = "";
    if (!items.length) {
        const li = document.createElement("li");
        li.textContent = "No strong warning for you.";
        recommendationsList.appendChild(li);
        return;
    }
    items.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = `${item.condition}: ${item.message}`;
        recommendationsList.appendChild(li);
    });
}

function renderMatches(matches) {
    matchedTableBody.innerHTML = "";
    if (!matches.length) {
        const row = document.createElement("tr");
        row.innerHTML = "<td colspan='5'>No matched ingredients available.</td>";
        matchedTableBody.appendChild(row);
        return;
    }
    matches.forEach((item) => {
        const row = document.createElement("tr");
        const cautions = item.caution_conditions && item.caution_conditions.length
            ? item.caution_conditions.join(", ")
            : "None";
        row.innerHTML = `
            <td>${item.ocr_ingredient}</td>
            <td>${item.matched_ingredient}</td>
            <td>${item.match_score}</td>
            <td>${item.health_score}</td>
            <td>${cautions}</td>
        `;
        matchedTableBody.appendChild(row);
    });
}

function renderResults(data) {
    scoreValue.textContent = data.score === null ? "--" : data.score;
    ratingLabel.textContent = data.rating;
    renderStars(data.star_count || 0);
    classificationBadge.textContent = data.classification;
    classificationBadge.className = `classification-badge ${classificationClass(data.classification)}`;
    renderPillList(ingredientList, data.ingredients || [], "No ingredients extracted");
    renderRecommendationList(data.recommendations || []);
    renderAdviceList(data.better_options || []);
    renderImportantIngredients(
        hazardIngredients,
        data.important_ingredients?.hazards || [],
        "No major hazard ingredient detected",
        "hazard"
    );
    renderImportantIngredients(
        goodIngredients,
        data.important_ingredients?.good || [],
        "No strong positive ingredient detected",
        "good"
    );
    renderMatches(data.matched || []);
    ocrText.textContent = data.text || "No OCR text returned.";
    adviceText.textContent = data.advice || "No advice available.";
    personalizedAdvice.textContent = data.personalized_advice || "";
}

const savedResult = sessionStorage.getItem("analysisResult");
if (!savedResult) {
    window.location.href = "/";
} else {
    renderResults(JSON.parse(savedResult));
}
