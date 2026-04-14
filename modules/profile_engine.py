"""
Module: profile_engine.py
Role: Save and load patient profiles locally (JSON file-based storage).
No database required for local use.
"""

import json
import os

PROFILE_PATH = "patient_profile.json"


def save_profile(data: dict) -> None:
    with open(PROFILE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_profile() -> dict:
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH) as f:
            return json.load(f)
    return {}