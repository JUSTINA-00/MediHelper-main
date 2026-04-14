"""
Module: drug_interaction.py
Role: Check new drugs in a document against the patient's current medications.

Uses a hardcoded interaction database for the most clinically critical pairs.
This covers the interactions most likely to be encountered in primary care.

For production: integrate with free DrugBank Community edition or
openFDA drug interaction API (both free).
"""

import re
from typing import List, Dict, Tuple


# ─────────────────────────────────────────────────────────────
# Interaction Database — hardcoded critical pairs
# Format: {(drug_a_canonical, drug_b_canonical): (severity, description)}
# ─────────────────────────────────────────────────────────────

INTERACTIONS: Dict[Tuple[str, str], Tuple[str, str]] = {
    ("warfarin", "aspirin"): (
        "HIGH",
        "Warfarin + Aspirin: Both thin the blood. Together they significantly increase the risk of serious bleeding. Only use together if specifically instructed by your doctor."
    ),
    ("warfarin", "ibuprofen"): (
        "HIGH",
        "Warfarin + Ibuprofen: Ibuprofen can increase warfarin's effect and cause dangerous bleeding. Avoid ibuprofen — use paracetamol for pain instead."
    ),
    ("warfarin", "naproxen"): (
        "HIGH",
        "Warfarin + Naproxen: Similar risk to warfarin + ibuprofen. Avoid naproxen."
    ),
    ("metformin", "ibuprofen"): (
        "MODERATE",
        "Metformin + Ibuprofen: Regular ibuprofen use can affect your kidneys, which may cause metformin to build up to unsafe levels. Use paracetamol where possible."
    ),
    ("metformin", "contrast dye"): (
        "HIGH",
        "Metformin + Contrast Dye (for scans): Metformin should usually be stopped before and after receiving contrast dye for scans. Tell your radiology team you take metformin."
    ),
    ("ace inhibitor", "potassium"): (
        "MODERATE",
        "ACE inhibitors + Potassium supplements: ACE inhibitors already raise potassium levels. Adding potassium supplements can cause dangerously high potassium."
    ),
    ("ace inhibitor", "nsaid"): (
        "MODERATE",
        "ACE inhibitors + NSAIDs (like ibuprofen): This combination can reduce the effectiveness of your blood pressure medication and harm your kidneys."
    ),
    ("ssri", "tramadol"): (
        "HIGH",
        "SSRIs + Tramadol: This combination can cause serotonin syndrome — a potentially dangerous condition with symptoms including agitation, rapid heart rate, and high temperature."
    ),
    ("ssri", "aspirin"): (
        "MODERATE",
        "SSRIs + Aspirin: Both can affect platelet function. Together they increase the risk of bleeding, especially stomach bleeding."
    ),
    ("simvastatin", "amiodarone"): (
        "HIGH",
        "Simvastatin + Amiodarone: Can cause serious muscle damage (rhabdomyolysis). Your doctor should review this combination."
    ),
    ("simvastatin", "clarithromycin"): (
        "HIGH",
        "Simvastatin + Clarithromycin (antibiotic): Clarithromycin raises simvastatin levels significantly, increasing the risk of muscle damage. Simvastatin may need to be stopped temporarily."
    ),
    ("lithium", "ibuprofen"): (
        "HIGH",
        "Lithium + Ibuprofen: Ibuprofen can raise lithium levels to toxic amounts. Avoid ibuprofen — use paracetamol."
    ),
    ("lithium", "ace inhibitor"): (
        "HIGH",
        "Lithium + ACE inhibitors: This combination can raise lithium to toxic levels. Regular lithium monitoring is essential."
    ),
    ("digoxin", "amiodarone"): (
        "HIGH",
        "Digoxin + Amiodarone: Amiodarone raises digoxin blood levels, which can cause toxicity. Your digoxin dose may need to be reduced."
    ),
    ("clopidogrel", "omeprazole"): (
        "MODERATE",
        "Clopidogrel + Omeprazole: Omeprazole can reduce how well clopidogrel works at preventing clots. Discuss alternative stomach-protection options with your doctor."
    ),
    ("fluoxetine", "tamoxifen"): (
        "HIGH",
        "Fluoxetine + Tamoxifen: Fluoxetine significantly reduces how well tamoxifen works at preventing breast cancer recurrence. An alternative antidepressant is usually recommended."
    ),
    ("ciprofloxacin", "warfarin"): (
        "HIGH",
        "Ciprofloxacin + Warfarin: This antibiotic can more than double warfarin's blood-thinning effect. Close INR monitoring is needed."
    ),
    ("rifampicin", "oral contraceptive"): (
        "HIGH",
        "Rifampicin + Oral Contraceptive: Rifampicin makes the contraceptive pill much less effective. Additional contraception is required."
    ),
    ("st john's wort", "ssri"): (
        "HIGH",
        "St John's Wort + SSRIs: Both affect serotonin. Combining them can cause serotonin syndrome."
    ),
    ("st john's wort", "warfarin"): (
        "HIGH",
        "St John's Wort + Warfarin: St John's Wort reduces warfarin's effectiveness, increasing clot risk."
    ),
    ("alcohol", "metronidazole"): (
        "HIGH",
        "Alcohol + Metronidazole: Do NOT drink alcohol during this course and for 48 hours after finishing. The combination causes severe nausea, vomiting, and flushing."
    ),
    ("alcohol", "benzodiazepine"): (
        "HIGH",
        "Alcohol + Benzodiazepines (e.g. diazepam, lorazepam): This combination dangerously suppresses breathing and the nervous system."
    ),
}


# ─────────────────────────────────────────────────────────────
# Drug synonym map — for matching drug names in documents
# ─────────────────────────────────────────────────────────────

DRUG_ALIASES: Dict[str, str] = {
    # Warfarin
    "warfarin": "warfarin", "coumadin": "warfarin",
    # Aspirin
    "aspirin": "aspirin", "acetylsalicylic acid": "aspirin", "disprin": "aspirin",
    # NSAIDs
    "ibuprofen": "ibuprofen", "brufen": "ibuprofen", "nurofen": "ibuprofen",
    "naproxen": "naproxen", "naprosyn": "naproxen",
    # Metformin
    "metformin": "metformin", "glucophage": "metformin",
    # Contrast
    "contrast": "contrast dye", "contrast medium": "contrast dye",
    "gadolinium": "contrast dye", "iodinated contrast": "contrast dye",
    # ACE inhibitors
    "ramipril": "ace inhibitor", "lisinopril": "ace inhibitor",
    "enalapril": "ace inhibitor", "perindopril": "ace inhibitor",
    # SSRIs
    "fluoxetine": "ssri", "sertraline": "ssri", "escitalopram": "ssri",
    "citalopram": "ssri", "paroxetine": "ssri", "prozac": "ssri",
    # Statins
    "simvastatin": "simvastatin", "zocor": "simvastatin",
    "atorvastatin": "atorvastatin", "lipitor": "atorvastatin",
    # Tramadol
    "tramadol": "tramadol",
    # Amiodarone
    "amiodarone": "amiodarone",
    # Clarithromycin
    "clarithromycin": "clarithromycin",
    # Lithium
    "lithium": "lithium",
    # Digoxin
    "digoxin": "digoxin", "lanoxin": "digoxin",
    # Clopidogrel
    "clopidogrel": "clopidogrel", "plavix": "clopidogrel",
    # Omeprazole
    "omeprazole": "omeprazole", "losec": "omeprazole", "prilosec": "omeprazole",
    # Tamoxifen
    "tamoxifen": "tamoxifen",
    # Fluoxetine
    "fluoxetine": "fluoxetine", "prozac": "fluoxetine",
    # Ciprofloxacin
    "ciprofloxacin": "ciprofloxacin", "cipro": "ciprofloxacin",
    # Rifampicin
    "rifampicin": "rifampicin", "rifampin": "rifampicin",
    # Hormonal contraceptives
    "oral contraceptive": "oral contraceptive", "contraceptive pill": "oral contraceptive",
    "combined pill": "oral contraceptive",
    # Herbal
    "st john's wort": "st john's wort", "hypericum": "st john's wort",
    # Alcohol
    "alcohol": "alcohol", "ethanol": "alcohol",
    # Metronidazole
    "metronidazole": "metronidazole", "flagyl": "metronidazole",
    # Benzodiazepines
    "diazepam": "benzodiazepine", "lorazepam": "benzodiazepine",
    "clonazepam": "benzodiazepine", "alprazolam": "benzodiazepine",
    "temazepam": "benzodiazepine",
    # Potassium
    "potassium": "potassium", "kcl": "potassium", "sando-k": "potassium",
    # Tramadol
    "tramadol": "tramadol", "tramal": "tramadol",
}


def _extract_drugs(text: str) -> List[str]:
    """Extract all drug canonical names found in the text."""
    text_lower = text.lower()
    found = []
    for alias, canonical in DRUG_ALIASES.items():
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, text_lower):
            if canonical not in found:
                found.append(canonical)
    return found


def check_interactions(document_text: str, patient_medications: List[str]) -> List[Dict]:
    """
    Find interactions between drugs mentioned in the document and
    the patient's current medications.
    Returns list of interaction warning dicts.
    """
    if not patient_medications:
        return []

    # Canonical forms of patient's current meds
    patient_canonical = []
    for med in patient_medications:
        canonical = DRUG_ALIASES.get(med.lower().strip(), med.lower().strip())
        patient_canonical.append(canonical)

    # Drugs mentioned in the new document
    doc_drugs = _extract_drugs(document_text)

    warnings = []
    checked_pairs = set()

    for doc_drug in doc_drugs:
        for patient_drug in patient_canonical:
            pair_sorted = tuple(sorted([doc_drug, patient_drug]))
            if pair_sorted in checked_pairs:
                continue
            checked_pairs.add(pair_sorted)

            # Check both orderings
            interaction = (
                INTERACTIONS.get((doc_drug, patient_drug)) or
                INTERACTIONS.get((patient_drug, doc_drug))
            )
            if interaction:
                severity, description = interaction
                warnings.append({
                    "drug_in_document": doc_drug,
                    "patient_medication": patient_drug,
                    "severity": severity,
                    "message": description,
                })

    return warnings