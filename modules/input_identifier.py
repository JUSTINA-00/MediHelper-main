"""
Module: input_identifier.py
Role: Detect what type of document/image was uploaded.
Returns: (doc_type_label, modality)
  modality = "text_pdf" | "handwritten_image" | "medical_image" | "typed_text"
"""

import os
import mimetypes


# ── Simple extension + MIME based routing (no model needed for this layer) ──

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
PDF_EXTENSIONS = {".pdf"}
TEXT_EXTENSIONS = {".txt", ".doc", ".docx"}


def identify_input(file_path: str) -> tuple[str, str]:
    """
    Returns (doc_type, modality).
    doc_type  — human-readable label e.g. 'Handwritten Prescription'
    modality  — routing key for downstream modules
    """
    ext = os.path.splitext(file_path)[1].lower()
    mime, _ = mimetypes.guess_type(file_path)

    if ext in PDF_EXTENSIONS:
        return _classify_pdf(file_path)

    if ext in TEXT_EXTENSIONS:
        return "Clinical Document", "typed_text"

    if ext in IMAGE_EXTENSIONS:
        return _classify_image(file_path)

    # Fallback
    return "Unknown Document", "typed_text"


def _classify_pdf(file_path: str) -> tuple[str, str]:
    """
    Try to detect if the PDF is a scanned image-only PDF or a text PDF.
    Uses pdfplumber for quick check.
    """
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            text = "".join(
                page.extract_text() or "" for page in pdf.pages[:2]
            )
        if len(text.strip()) > 50:
            doc_type = _classify_text_content(text)
            return doc_type, "text_pdf"
        else:
            # Scanned / image PDF
            return "Scanned Medical Document", "handwritten_image"
    except Exception:
        return "Medical PDF", "text_pdf"


def _classify_image(file_path: str) -> tuple[str, str]:
    """
    Heuristic: try to determine if this is a handwritten prescription
    or a medical scan/photograph.
    Uses a lightweight classifier via transformers if available,
    otherwise falls back to hardcoded keyword heuristic after OCR.
    """
    try:
        # Try lightweight CLIP-based zero-shot classification
        from transformers import pipeline
        classifier = pipeline(
            "zero-shot-image-classification",
            model="openai/clip-vit-base-patch32",  # Free, ~600MB, runs locally
        )
        candidate_labels = [
            "handwritten prescription",
            "X-ray",
            "MRI scan",
            "CT scan",
            "ECG electrocardiogram",
            "skin dermoscopy photograph",
            "blood test lab report",
            "eye fundus photograph",
        ]
        result = classifier(file_path, candidate_labels)
        top_label = result[0]["label"]
        score = result[0]["score"]

        if score < 0.3:
            return "Medical Image", "medical_image"

        if "prescription" in top_label.lower():
            return "Handwritten Prescription", "handwritten_image"
        else:
            return top_label.title(), "medical_image"

    except Exception:
        # Fallback: treat any image as a medical image
        return "Medical Image", "medical_image"


def _classify_text_content(text: str) -> str:
    """
    Keyword-based document type detection from extracted text.
    Hardcoded — reliable, free, no model needed.
    """
    text_lower = text.lower()

    rules = [
        (["discharge summary", "discharged", "admission date", "discharge date"], "Discharge Summary"),
        (["radiology", "x-ray", "mri", "ct scan", "ultrasound", "findings:", "impression:"], "Radiology Report"),
        (["haemoglobin", "wbc", "platelet", "glucose", "creatinine", "hba1c", "cholesterol"], "Lab Results"),
        (["prescribed", "take", "tablet", "capsule", "mg", "bd", "od", "tds", "prn", "nocte"], "Prescription"),
        (["ecg", "electrocardiogram", "heart rate", "rhythm", "sinus"], "ECG Report"),
        (["clinic", "follow-up", "reviewed", "assessment:", "plan:"], "Clinical Note"),
        (["operation", "procedure", "intraoperative", "post-operative", "anaesthesia"], "Operative Report"),
    ]

    for keywords, label in rules:
        if any(k in text_lower for k in keywords):
            return label

    return "Medical Document"