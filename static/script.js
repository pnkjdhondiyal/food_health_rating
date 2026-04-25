const form = document.getElementById("analyze-form");
const dropZone = document.getElementById("drop-zone");
const imageInput = document.getElementById("image-input");
const fileName = document.getElementById("file-name");
const analyzeButton = document.getElementById("analyze-button");
const loadingState = document.getElementById("loading-state");
const errorMessage = document.getElementById("error-message");

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

        sessionStorage.setItem("analysisResult", JSON.stringify(data));
        window.location.href = "/results";
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
