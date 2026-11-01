"""Saves the farmer's own inputs (place, crop, quantity) to a local file. This is user input, not sample data."""
import json, os
from pathlib import Path

PATH = Path(os.getenv("FASAL_PROFILE_PATH", Path(__file__).resolve().parent.parent / "farm_profile.json"))


def load():
    try:
        return json.loads(Path(PATH).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save(d):
    Path(PATH).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
