from pathlib import Path

import cv2
import pytesseract


TESSERACT_CONFIG = "--psm 6"


def _configure_tesseract() -> None:
    """Set a common Windows install path if Tesseract is available there."""
    default_windows_path = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if default_windows_path.exists():
        pytesseract.pytesseract.tesseract_cmd = str(default_windows_path)


def _preprocess_image(image_path: str):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Could not read the uploaded image.")

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(grayscale, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    blurred = cv2.GaussianBlur(resized, (5, 5), 0)
    thresholded = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )
    return thresholded


def extract_text(image_path: str) -> str:
    """Extract text from a packaged food label image."""
    _configure_tesseract()
    processed_image = _preprocess_image(image_path)
    extracted_text = pytesseract.image_to_string(processed_image, config=TESSERACT_CONFIG)
    return extracted_text.strip()
