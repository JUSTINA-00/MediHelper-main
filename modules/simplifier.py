"""
Module: simplifier.py
Role: Convert raw medical text into plain-language output.

Strategy (all FREE, no API tokens):
  1. Primary: Use a local instruction-following model via Ollama
     (e.g. llama3.2:3b or mistral:7b — user runs `ollama pull llama3.2`)
  2. Fallback: Rule-based simplification using curated jargon dictionary
     + sentence restructuring with spaCy (free, local)

This keeps the pipeline completely free and offline-capable.
"""

import re
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Medical Jargon → Plain English Dictionary (hardcoded, curated)
# ─────────────────────────────────────────────────────────────

JARGON_MAP = {
    # Anatomy & physiology
    "myocardial infarction": "heart attack",
    "cerebrovascular accident": "stroke",
    "hypertension": "high blood pressure",
    "hypotension": "low blood pressure",
    "tachycardia": "fast heart rate",
    "bradycardia": "slow heart rate",
    "dyspnoea": "shortness of breath",
    "dyspnea": "shortness of breath",
    "haemoptysis": "coughing up blood",
    "haematuria": "blood in urine",
    "pyrexia": "fever",
    "afebrile": "no fever",
    "oedema": "swelling caused by fluid",
    "edema": "swelling caused by fluid",
    "erythema": "redness of the skin",
    "pruritus": "itching",
    "malaise": "general feeling of being unwell",
    "nausea": "feeling sick / urge to vomit",
    "emesis": "vomiting",
    "haemorrhage": "bleeding",
    "hemorrhage": "bleeding",
    "contusion": "bruise",
    "laceration": "cut or tear in the skin",
    "fracture": "broken bone",
    "syncope": "fainting",
    "vertigo": "dizziness with spinning sensation",
    "palpitations": "awareness of your heartbeat, often fast or irregular",
    "dysphagia": "difficulty swallowing",
    "aphasia": "difficulty speaking or understanding language",
    "ataxia": "loss of coordination",
    # Lab / measurements
    "egfr": "kidney filtration rate",
    "hba1c": "average blood sugar over 3 months",
    "bmi": "body mass index (weight-to-height ratio)",
    "creatinine": "waste product — high levels may indicate kidney issues",
    "haemoglobin": "protein in red blood cells that carries oxygen",
    "wbc": "white blood cell count (part of immune system)",
    "platelet": "blood cell that helps clotting",
    "troponin": "protein released when heart muscle is damaged",
    "bnp": "hormone released when heart is under stress",
    "glucose": "blood sugar level",
    "cholesterol": "fatty substance in blood",
    "ldl": "bad cholesterol",
    "hdl": "good cholesterol",
    "triglycerides": "type of fat in blood",
    # Diagnoses
    "type 2 diabetes mellitus": "Type 2 diabetes (raised blood sugar)",
    "diabetes mellitus": "diabetes (raised blood sugar)",
    "chronic kidney disease": "long-term kidney damage",
    "ckd": "chronic kidney disease (long-term kidney damage)",
    "copd": "chronic obstructive pulmonary disease (lung disease causing breathing difficulty)",
    "mi": "heart attack",
    "cva": "stroke",
    "dvt": "deep vein thrombosis (blood clot in a leg vein)",
    "pe": "pulmonary embolism (blood clot in the lungs)",
    "uti": "urinary tract infection (bladder/kidney infection)",
    "urti": "upper respiratory tract infection (cold or sore throat)",
    # Imaging
    "consolidation": "area of lung filled with fluid or infection",
    "effusion": "abnormal build-up of fluid",
    "pleural effusion": "fluid around the lungs",
    "cardiomegaly": "enlarged heart",
    "pneumonia": "lung infection",
    "atelectasis": "collapsed or partially collapsed lung",
    "opacity": "area appearing white/grey on scan, may suggest fluid or tissue change",
    "lucency": "area appearing darker on scan",
    "lytic lesion": "area where bone has been destroyed",
    "degenerative changes": "wear-and-tear changes, common with age",
    "osteophyte": "bone spur (bony projection that forms on joints)",
    "spondylosis": "age-related wear of the spine",
    "hernia": "when an organ pushes through a weak spot in surrounding tissue",
    "calcification": "calcium deposits (hardening of tissue)",
    # Treatment terms
    "prophylaxis": "preventive treatment",
    "analgesic": "pain reliever",
    "antipyretic": "fever-reducing medicine",
    "antiemetic": "anti-nausea medicine",
    "anticoagulant": "blood thinner",
    "bronchodilator": "medicine that opens up the airways",
    "diuretic": "medicine that helps remove excess fluid through urine",
    "contraindicated": "should NOT be used / not safe in this situation",
    "indicated": "recommended / appropriate for this situation",
    "titrated": "dose adjusted gradually",
    "loading dose": "higher first dose to quickly reach effective levels",
    "maintenance dose": "regular ongoing dose",
    "prognosis": "expected outcome or course of the condition",
    "benign": "not cancerous / not harmful",
    "malignant": "cancerous",
    "idiopathic": "cause is unknown",
    "acute": "sudden onset, short-term",
    "chronic": "long-lasting or recurring",
    "bilateral": "on both sides",
    "unilateral": "on one side only",
    "proximal": "closer to the centre of the body",
    "distal": "further from the centre of the body",
    "anterior": "front",
    "posterior": "back",
    "superior": "above",
    "inferior": "below",
    "lateral": "to the side",
    "medial": "towards the middle",
}


# ─────────────────────────────────────────────────────────────
# Jargon replacement (hardcoded layer — always runs)
# ─────────────────────────────────────────────────────────────

def replace_jargon(text: str) -> str:
    """Replace known medical jargon with plain equivalents."""
    for term, plain in sorted(JARGON_MAP.items(), key=lambda x: -len(x[0])):
        pattern = r'\b' + re.escape(term) + r'\b'
        text = re.sub(pattern, plain, text, flags=re.IGNORECASE)
    return text


# ─────────────────────────────────────────────────────────────
# Ollama-based LLM simplification (free, local, no API tokens)
# Install: https://ollama.com → then: ollama pull llama3.2
# ─────────────────────────────────────────────────────────────

def _simplify_with_ollama(text: str, doc_type: str, profile: dict) -> Optional[str]:
    """
    Call a locally-running Ollama LLM to simplify the text.
    Returns None if Ollama is not running (fallback to rule-based).
    """
    try:
        import requests
        profile_context = _build_profile_context(profile)
        prompt = f"""You are a medical document simplifier. Your job is to rewrite medical documents in plain, friendly English that any patient can understand.

Document type: {doc_type}
Patient profile: {profile_context}

Rules:
- Write at a Grade 6 reading level
- Use short sentences (under 20 words each)
- Convert passive voice to active voice
- Explain any number with context (e.g. "your eGFR is 45 — normal is above 60")
- Break medication instructions into: drug name, dose, when to take, for how long
- DO NOT invent information not in the original
- DO NOT remove any medically important detail

After the plain summary, add a section titled "What This Means For You" that references the patient's specific conditions, medications, and history.

Medical document to simplify:
{text}

Output format:
PLAIN SUMMARY:
[plain language version here]

WHAT THIS MEANS FOR YOU:
[personalised section here]"""

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        result = response.json().get("response", "")
        return result
    except Exception:
        return None  # Signal to use fallback


# ─────────────────────────────────────────────────────────────
# Rule-based fallback simplifier (no model required)
# ─────────────────────────────────────────────────────────────

def _simplify_rule_based(text: str, doc_type: str, profile: dict) -> dict:
    """
    Pure rule-based simplification when no LLM is available.
    Good for structured documents (labs, prescriptions, discharge summaries).
    """
    # Step 1: Replace jargon
    simplified = replace_jargon(text)

    # Step 2: Break long sentences
    simplified = _break_long_sentences(simplified)

    # Step 3: Remove/replace clinical passive voice patterns
    simplified = _fix_passive_voice(simplified)

    # Step 4: Add contextual numbers
    simplified = _contextualise_numbers(simplified)

    # Step 5: Generate personalised section
    personalised = _build_personalised_section(simplified, profile)

    return {
        "plain_summary": simplified,
        "personalised_section": personalised,
        "confidence": 0.70,  # Lower confidence for rule-based
        "method": "rule-based",
    }


def _break_long_sentences(text: str) -> str:
    """Split sentences over 30 words at natural conjunction points."""
    conjunctions = [" however ", " although ", " because ", " therefore ", " which ", " whereby "]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) > 30:
            for conj in conjunctions:
                if conj in sentence.lower():
                    parts = re.split(re.escape(conj), sentence, flags=re.IGNORECASE, maxsplit=1)
                    sentence = ". ".join(p.strip().capitalize() for p in parts)
                    break
        result.append(sentence)
    return " ".join(result)


def _fix_passive_voice(text: str) -> str:
    """Replace common clinical passive constructions."""
    replacements = [
        (r"was found to be", "is"),
        (r"it was noted that", ""),
        (r"it was decided to", "your doctor decided to"),
        (r"patient was advised", "you were advised"),
        (r"patient should", "you should"),
        (r"patient is", "you are"),
        (r"the patient", "you"),
        (r"this patient", "you"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _contextualise_numbers(text: str) -> str:
    """Add context to known lab values when found."""
    reference_ranges = {
        r"egfr[:\s]+(\d+\.?\d*)": (
            "eGFR (kidney filtration rate): {val} mL/min — "
            "normal is above 60. {note}",
            lambda v: "This is below normal — discuss with your doctor." if float(v) < 60 else "This is within the normal range."
        ),
        r"hba1c[:\s]+(\d+\.?\d*)": (
            "HbA1c (3-month blood sugar average): {val}% — "
            "target for diabetes is usually below 7%. {note}",
            lambda v: "This is above target — your blood sugar control may need review." if float(v) > 7 else "This is within the target range."
        ),
        r"haemoglobin[:\s]+(\d+\.?\d*)": (
            "Haemoglobin (oxygen-carrying protein): {val} g/dL — "
            "normal is 12–17 g/dL. {note}",
            lambda v: "This is below normal — you may have anaemia." if float(v) < 12 else "This is within the normal range."
        ),
    }
    for pattern, (template, note_fn) in reference_ranges.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            val = match.group(1)
            note = note_fn(val)
            replacement = template.format(val=val, note=note)
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _build_profile_context(profile: dict) -> str:
    parts = []
    if profile.get("age"):
        parts.append(f"Age {profile['age']}, {profile.get('gender', '')}")
    if profile.get("diagnoses"):
        parts.append(f"Conditions: {', '.join(profile['diagnoses'])}")
    if profile.get("medications"):
        parts.append(f"Medications: {', '.join(profile['medications'])}")
    if profile.get("allergies"):
        parts.append(f"Allergies: {', '.join(profile['allergies'])}")
    if profile.get("surgeries"):
        parts.append(f"Past surgeries: {', '.join(profile['surgeries'])}")
    return "; ".join(parts) if parts else "No profile data provided"


def _build_personalised_section(text: str, profile: dict) -> str:
    """
    Build a personalised paragraph referencing the patient's known conditions.
    Rule-based pattern matching.
    """
    lines = []
    text_lower = text.lower()

    diagnoses = profile.get("diagnoses", [])
    medications = profile.get("medications", [])
    surgeries = profile.get("surgeries", [])

    for condition in diagnoses:
        cond_lower = condition.lower()
        if any(kw in text_lower for kw in [cond_lower, "blood sugar", "glucose", "egfr", "kidney"]):
            lines.append(
                f"This document is relevant to your {condition}. "
                "Please discuss the results with your doctor at your next appointment."
            )

    for med in medications:
        if med.lower() in text_lower:
            lines.append(
                f"Your current medication {med} is mentioned in this document. "
                "Make sure your doctor knows you are already taking it."
            )

    for surgery in surgeries:
        if any(kw in text_lower for kw in [surgery.lower(), "post-op", "surgical", "procedure"]):
            lines.append(
                f"Your past {surgery} may be relevant to what is described in this document."
            )

    if not lines:
        lines.append(
            "Based on your profile, there are no immediate specific concerns "
            "with this document — but always discuss results with your doctor."
        )

    return " ".join(lines)


# ─────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────

def simplify_document(text: str, doc_type: str, profile: dict) -> dict:
    """
    Attempt LLM simplification via Ollama first.
    Falls back to rule-based simplification if Ollama is not available.
    """
    # Always run jargon replacement first as a pre-processing step
    preprocessed_text = replace_jargon(text)

    # Try Ollama LLM
    llm_result = _simplify_with_ollama(preprocessed_text, doc_type, profile)

    if llm_result:
        # Parse LLM output
        plain = ""
        personal = ""
        if "WHAT THIS MEANS FOR YOU:" in llm_result:
            parts = llm_result.split("WHAT THIS MEANS FOR YOU:", 1)
            plain = parts[0].replace("PLAIN SUMMARY:", "").strip()
            personal = parts[1].strip()
        else:
            plain = llm_result.strip()
            personal = _build_personalised_section(plain, profile)

        return {
            "plain_summary": plain,
            "personalised_section": personal,
            "confidence": 0.88,
            "method": "llm-ollama",
        }

    # Fallback to rule-based
    return _simplify_rule_based(preprocessed_text, doc_type, profile)