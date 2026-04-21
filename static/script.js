const form = document.getElementById("analyze-form");
const uploadPanel = document.getElementById("upload-panel");
const dropZone = document.getElementById("drop-zone");
const imageInput = document.getElementById("image-input");
const fileName = document.getElementById("file-name");
const analyzeButton = document.getElementById("analyze-button");
const analyzeAnotherButton = document.getElementById("analyze-another-button");
const loadingState = document.getElementById("loading-state");
const errorMessage = document.getElementById("error-message");
const resultsPanel = document.getElementById("results-panel");
const scoreValue = document.getElementById("score-value");
const starRating = document.getElementById("star-rating");
const ratingLabel = document.getElementById("rating-label");
const classificationBadge = document.getElementById("classification-badge");
const ingredientList = document.getElementById("ingredient-list");
const ocrText = document.getElementById("ocr-text");
const matchedTableBody = document.getElementById("matched-table-body");
const adviceText = document.getElementById("advice-text");
const recommendationsList = document.getElementById("recommendations-list");
const betterOptions = document.getElementById("better-options");

function setLoading(isLoading) {
    analyzeButton.disabled = isLoading;
    loadingState.classList.toggle("hidden", !isLoading);
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove("hidden");
}

function clearError() {
    errorMessage.textContent = "";
    errorMessage.classList.add("hidden");
}

function updateFileName(file) {
    fileName.textContent = file ? file.name : "No file selected";
}

function renderStars(count) {
    const fullCount = Number.isFinite(count) ? count : 0;
    const filled = "\u2605".repeat(fullCount);
    const empty = "\u2606".repeat(Math.max(5 - fullCount, 0));
    starRating.textContent = filled + empty;
}

function classificationClass(value) {
    return String(value || "Moderate").toLowerCase().replace(/\s+/g, "-");
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

function renderRecommendationList(items) {
    recommendationsList.innerHTML = "";

    if (!items.length) {
        const li = document.createElement("li");
        li.textContent = "No strong illness-specific warning was detected from the current dataset.";
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
        row.innerHTML = "<td colspan='4'>No matched ingredients available.</td>";
        matchedTableBody.appendChild(row);
        return;
    }

    matches.forEach((item) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${item.ocr_ingredient}</td>
            <td>${item.matched_ingredient}</td>
            <td>${item.match_score}</td>
            <td>${item.health_score}</td>
        `;
        matchedTableBody.appendChild(row);
    });
}

function renderResults(data) {
    resultsPanel.classList.remove("hidden");
    uploadPanel.classList.add("hidden");
    scoreValue.textContent = data.score === null ? "--" : data.score;
    ratingLabel.textContent = data.rating;
    renderStars(data.star_count || 0);
    classificationBadge.textContent = data.classification;
    classificationBadge.className = `classification-badge ${classificationClass(data.classification)}`;
    renderPillList(ingredientList, data.ingredients || [], "No ingredients extracted");
    renderRecommendationList(data.recommendations || []);
    renderAdviceList(data.better_options || []);
    renderMatches(data.matched || []);
    ocrText.textContent = data.text || "No OCR text returned.";
    adviceText.textContent = data.advice || "No advice available.";
    window.scrollTo({ top: 0, behavior: "smooth" });
}

async function analyzeFile(file) {
    const formData = new FormData();
    formData.append("image", file);

    clearError();
    setLoading(true);

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Analysis failed.");
        }

        renderResults(data);
    } catch (error) {
        showError(error.message || "Something went wrong while analyzing the image.");
    } finally {
        setLoading(false);
    }
}

imageInput.addEventListener("change", () => {
    const [file] = imageInput.files;
    updateFileName(file);
});

analyzeAnotherButton.addEventListener("click", () => {
    resultsPanel.classList.add("hidden");
    uploadPanel.classList.remove("hidden");
    imageInput.value = "";
    updateFileName(null);
    clearError();
    window.scrollTo({ top: 0, behavior: "smooth" });
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const [file] = imageInput.files;

    if (!file) {
        showError("Please choose an image before analyzing.");
        return;
    }

    await analyzeFile(file);
});

["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add("drag-active");
    });
});

["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove("drag-active");
    });
});

dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (!file) {
        return;
    }

    imageInput.files = event.dataTransfer.files;
    updateFileName(file);
});
