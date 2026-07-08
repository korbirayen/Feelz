from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_SCRIPT = ROOT / "Sentiment247.py"
REQUIREMENTS = ROOT / "requirements.txt"
NLTK_RESOURCES = {
    "punkt": "tokenizers/punkt",
    "punkt_tab": "tokenizers/punkt_tab",
    "stopwords": "corpora/stopwords",
    "vader_lexicon": "sentiment/vader_lexicon",
}
REQUIRED_MODULES = [
    "emoji",
    "nltk",
    "numpy",
    "pandas",
    "PIL",
    "requests",
    "sklearn",
    "sounddevice",
    "speech_recognition",
    "validators",
]


def has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def ensure_dependencies() -> None:
    missing = [module for module in REQUIRED_MODULES if not has_module(module)]
    if missing:
        print("Installing missing Python packages:", ", ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)])


def ensure_nltk_data() -> None:
    try:
        import nltk
    except Exception:
        return

    for package, resource_path in NLTK_RESOURCES.items():
        try:
            nltk.data.find(resource_path)
        except LookupError:
            print(f"Downloading NLTK resource: {package}")
            nltk.download(package, quiet=True)


def main() -> int:
    os.chdir(ROOT)
    ensure_dependencies()
    ensure_nltk_data()
    return subprocess.call([sys.executable, str(APP_SCRIPT)])


if __name__ == "__main__":
    raise SystemExit(main())
