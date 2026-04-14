"""
Module: ocr_processor.py
Role: Extract text from any input modality.
  - text_pdf      → pdfplumber (fast, free, no model)
  - typed_text    → read directly
  - handwritten_image → TrOCR (free HuggingFace model) + abbreviation expander
  - medical_image → BioViL-T or BLIP-2 image captioning (free HuggingFace)
"""

import os
from PIL import Image


# ─────────────────────────────────────────────────────────────
# Prescription Abbreviation Dictionary (hardcoded — exhaustive)
# ─────────────────────────────────────────────────────────────
PRESCRIPTION_ABBREVIATIONS = {
    # Frequency
    "od": "once daily",
    "bd": "twice daily",
    "bid": "twice daily",
    "tds": "three times daily",
    "tid": "three times daily",
    "qds": "four times daily",
    "qid": "four times daily",
    "prn": "as needed",
    "sos": "if required",
    "stat": "immediately (one dose only)",
    "nocte": "at night",
    "mane": "in the morning",
    "ac": "before meals",
    "pc": "after meals",
    "cc": "with meals",
    # Route
    "po": "by mouth (oral)",
    "sl": "under the tongue (sublingual)",
    "im": "into the muscle (intramuscular injection)",
    "iv": "into the vein (intravenous)",
    "sc": "under the skin (subcutaneous)",
    "top": "apply to skin (topical)",
    "inh": "inhaled",
    "pr": "rectally",
    # Quantity
    "tabs": "tablets",
    "tab": "tablet",
    "cap": "capsule",
    "caps": "capsules",
    "ml": "millilitres",
    "mcg": "micrograms",
    "mg": "milligrams",
    "g": "grams",
    "u": "units",
    # Other
    "mitte": "dispense",
    "rep": "repeat",
    "sig": "directions",
    "disp": "dispense",
    "dtd": "give of such doses",
    "nkda": "no known drug allergies",
}


def expand_abbreviations(text: str) -> str:
    """
    Replace known prescription abbreviations with full English phrases.
    Case-insensitive, word-boundary aware.
    """
    import re
    for abbr, expansion in PRESCRIPTION_ABBREVIATIONS.items():
        pattern = r'\b' + re.escape(abbr) + r'\b'
        text = re.sub(pattern, expansion, text, flags=re.IGNORECASE)
    return text


# ─────────────────────────────────────────────────────────────
# Main dispatcher
# ─────────────────────────────────────────────────────────────

def extract_text(file_path: str, modality: str) -> str:
    """
    Routes to the correct extraction method based on modality.
    Returns raw extracted text string.
    """
    if modality == "text_pdf":
        return _extract_pdf_text(file_path)

    if modality == "typed_text":
        return _extract_plain_text(file_path)

    if modality == "handwritten_image":
        return _extract_handwritten(file_path)

    if modality == "medical_image":
        return _describe_medical_image(file_path)

    return ""


# ─────────────────────────────────────────────────────────────
# PDF text extraction
# ─────────────────────────────────────────────────────────────

def _extract_pdf_text(file_path: str) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()
    except Exception as e:
        return f"[PDF extraction error: {e}]"


# ─────────────────────────────────────────────────────────────
# Plain text / typed document
# ─────────────────────────────────────────────────────────────

def _extract_plain_text(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"[Text read error: {e}]"


# ─────────────────────────────────────────────────────────────
# Handwritten image OCR — TrOCR (free, runs locally)
# Model: microsoft/trocr-large-handwritten  (~1.3GB, one-time download)
# ─────────────────────────────────────────────────────────────

_trocr_model = None
_trocr_processor = None

def _load_trocr():
    global _trocr_model, _trocr_processor
    if _trocr_model is None:
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        print("[MediPlain] Loading TrOCR handwriting model (first run only)...")
        _trocr_processor = TrOCRProcessor.from_pretrained(
            "microsoft/trocr-large-handwritten"
        )
        _trocr_model = VisionEncoderDecoderModel.from_pretrained(
            "microsoft/trocr-large-handwritten"
        )
        print("[MediPlain] TrOCR loaded.")


def _extract_handwritten(file_path: str) -> str:
    try:
        _load_trocr()
        import torch
        image = Image.open(file_path).convert("RGB")
        pixel_values = _trocr_processor(image, return_tensors="pt").pixel_values
        with torch.no_grad():
            generated_ids = _trocr_model.generate(pixel_values)
        text = _trocr_processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]
        # Expand prescription abbreviations after OCR
        text = expand_abbreviations(text)
        return text
    except Exception as e:
        return f"[Handwriting OCR error: {e}]"


# ─────────────────────────────────────────────────────────────
# Medical image description — BLIP-2 (free, runs locally)
# Model: Salesforce/blip2-opt-2.7b  (~6GB) OR
#        Salesforce/blip-image-captioning-base (~1GB, lighter option)
# Using lighter model by default; switch to blip2 for better accuracy.
# ─────────────────────────────────────────────────────────────

_blip_model = None
_blip_processor = None

def _load_blip():
    global _blip_model, _blip_processor
    if _blip_model is None:
        from transformers import BlipProcessor, BlipForConditionalGeneration
        print("[MediPlain] Loading BLIP image captioning model (first run only)...")
        _blip_processor = BlipProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )
        _blip_model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base"
        )
        print("[MediPlain] BLIP loaded.")


def _describe_medical_image(file_path: str) -> str:
    try:
        _load_blip()
        import torch
        image = Image.open(file_path).convert("RGB")
        inputs = _blip_processor(image, return_tensors="pt")
        with torch.no_grad():
            out = _blip_model.generate(**inputs, max_new_tokens=200)
        caption = _blip_processor.decode(out[0], skip_special_tokens=True)
        return f"[Medical Image Analysis]\n{caption}"
    except Exception as e:
        return f"[Image description error: {e}]"