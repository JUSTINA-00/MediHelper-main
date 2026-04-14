"""
Module: allergy_checker.py
Role: Scan incoming document text for allergens listed in the patient profile.
      Raises prominent warnings BEFORE any other output.

Approach: Hardcoded synonym map + fuzzy string matching (rapidfuzz, free).
No model needed — fast and reliable.
"""

import re
from typing import List, Dict


# ─────────────────────────────────────────────────────────────
# Drug / allergen synonym map
# Covers common allergen name variants in medical documents
# ─────────────────────────────────────────────────────────────

ALLERGEN_SYNONYMS: Dict[str, List[str]] = {
    "penicillin": [
        "penicillin", "amoxicillin", "amoxycillin", "ampicillin",
        "flucloxacillin", "co-amoxiclav", "augmentin", "phenoxymethylpenicillin",
        "piperacillin", "tazobactam", "piptaz",
    ],
    "aspirin": [
        "aspirin", "acetylsalicylic acid", "asa", "disprin",
        "salicylate", "salicylic acid",
    ],
    "nsaids": [
        "ibuprofen", "naproxen", "diclofenac", "indomethacin", "celecoxib",
        "mefenamic acid", "piroxicam", "ketoprofen", "nsaid",
    ],
    "sulfa": [
        "sulfonamide", "sulfamethoxazole", "trimethoprim-sulfamethoxazole",
        "co-trimoxazole", "septrin", "bactrim", "sulfa",
    ],
    "cephalosporins": [
        "cephalexin", "cefalexin", "cefuroxime", "ceftriaxone",
        "cefotaxime", "cephalosporin", "cefazolin",
    ],
    "latex": ["latex", "rubber"],
    "iodine": ["iodine", "iodide", "contrast dye", "contrast medium", "gadolinium"],
    "codeine": ["codeine", "co-codamol", "co-dydramol", "dihydrocodeine"],
    "morphine": ["morphine", "diamorphine", "heroin", "ms contin", "oramorph"],
    "opioids": [
        "opioid", "oxycodone", "hydrocodone", "fentanyl", "tramadol",
        "buprenorphine", "methadone",
    ],
    "metformin": ["metformin", "glucophage", "glucomet"],
    "statins": [
        "statin", "atorvastatin", "simvastatin", "rosuvastatin",
        "pravastatin", "fluvastatin", "lipitor", "crestor", "zocor",
    ],
    "ace inhibitors": [
        "ramipril", "lisinopril", "enalapril", "perindopril",
        "captopril", "ace inhibitor", "acei",
    ],
    "beta blockers": [
        "bisoprolol", "metoprolol", "atenolol", "propranolol",
        "carvedilol", "labetalol", "beta blocker",
    ],
    "warfarin": ["warfarin", "coumadin"],
    "vancomycin": ["vancomycin"],
    "gentamicin": ["gentamicin", "aminoglycoside"],
    "tetracycline": ["tetracycline", "doxycycline", "minocycline"],
    "metronidazole": ["metronidazole", "flagyl"],
    "fluconazole": ["fluconazole", "diflucan"],
    "carbamazepine": ["carbamazepine", "tegretol"],
    "phenytoin": ["phenytoin", "dilantin"],
    "allopurinol": ["allopurinol", "zyloric"],
}


def _normalise(text: str) -> str:
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower())


def _build_synonym_set(allergen: str) -> List[str]:
    """Return all synonyms for a given allergen name."""
    allergen_lower = allergen.lower().strip()
    # Direct match
    if allergen_lower in ALLERGEN_SYNONYMS:
        return ALLERGEN_SYNONYMS[allergen_lower]
    # Partial key match (e.g. "amoxicillin" maps to "penicillin" group)
    for key, synonyms in ALLERGEN_SYNONYMS.items():
        if allergen_lower in synonyms or allergen_lower == key:
            return synonyms
    # No match — just use the raw allergen name
    return [allergen_lower]


def check_allergies(document_text: str, patient_allergies: List[str]) -> List[Dict]:
    """
    Scan document_text for any substances matching the patient's allergy list.
    Returns a list of warning dicts, one per allergen match found.
    """
    if not patient_allergies:
        return []

    warnings = []
    doc_normalised = _normalise(document_text)

    for allergen in patient_allergies:
        synonyms = _build_synonym_set(allergen)
        found_terms = []

        for synonym in synonyms:
            # Exact word-boundary match
            pattern = r'\b' + re.escape(synonym.lower()) + r'\b'
            if re.search(pattern, doc_normalised):
                found_terms.append(synonym)

        # Try fuzzy matching for misspellings (uses rapidfuzz if available)
        if not found_terms:
            found_terms = _fuzzy_check(allergen, synonyms, doc_normalised)

        if found_terms:
            warnings.append({
                "allergen": allergen,
                "found_terms": list(set(found_terms)),
                "severity": "HIGH",
                "message": (
                    f"⚠️ ALLERGY ALERT: This document mentions {', '.join(set(found_terms))}. "
                    f"Your profile shows you are allergic to {allergen}. "
                    "Do NOT take this medication. Contact your prescriber immediately."
                ),
            })

    return warnings


def _fuzzy_check(allergen: str, synonyms: List[str], doc_text: str) -> List[str]:
    """
    Use rapidfuzz for approximate matching in case of OCR typos.
    Falls back gracefully if rapidfuzz is not installed.
    """
    try:
        from rapidfuzz import fuzz, process
        words = doc_text.split()
        found = []
        for synonym in synonyms:
            # Find any word in document within edit distance
            match = process.extractOne(
                synonym, words, scorer=fuzz.ratio, score_cutoff=88
            )
            if match:
                found.append(synonym)
        return found
    except ImportError:
        return []  # Fuzzy matching not available, skip