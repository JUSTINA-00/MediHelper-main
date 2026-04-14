"""
MediPlain — Main Flask Application Entry Point
Run: python app.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os

from modules.input_identifier import identify_input
from modules.ocr_processor import extract_text
from modules.simplifier import simplify_document
from modules.profile_engine import load_profile, save_profile
from modules.allergy_checker import check_allergies
from modules.drug_interaction import check_interactions

app = Flask(__name__)
CORS(app)  # Allow React frontend to call this API

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ──────────────────────────────────────────────
# Route: Save patient profile
# ──────────────────────────────────────────────
@app.route("/api/profile", methods=["POST"])
def profile():
    data = request.json
    save_profile(data)
    return jsonify({"status": "saved"})


# ──────────────────────────────────────────────
# Route: Analyse an uploaded document
# ──────────────────────────────────────────────
@app.route("/api/analyse", methods=["POST"])
def analyse():
    file = request.files.get("file")
    profile_data = request.form.get("profile", "{}")

    import json
    profile = json.loads(profile_data)

    # 1. Save uploaded file temporarily
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # 2. Identify what the input is
    doc_type, modality = identify_input(file_path)

    # 3. Extract text (OCR / direct / image description)
    raw_text = extract_text(file_path, modality)

    # 4. Check allergies FIRST — before anything else
    allergy_warnings = check_allergies(raw_text, profile.get("allergies", []))

    # 5. Check drug interactions
    interaction_warnings = check_interactions(
        raw_text, profile.get("medications", [])
    )

    # 6. Simplify the document
    simplified = simplify_document(raw_text, doc_type, profile)

    # 7. Assemble final response
    result = {
        "doc_type": doc_type,
        "modality": modality,
        "allergy_warnings": allergy_warnings,
        "interaction_warnings": interaction_warnings,
        "plain_summary": simplified["plain_summary"],
        "personalised_section": simplified["personalised_section"],
        "technical_text": raw_text,
        "confidence": simplified.get("confidence", 0.85),
    }

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)