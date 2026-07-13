"""Optional multi-class emotion model (joy/sadness/anger/fear/...) via a
small HuggingFace transformer.

This is an enhancement layered on top of - not a replacement for - the
sklearn depression-language pipeline in DepressionScore.py: that model is
fast, fully offline, and thoroughly evaluated (see MODEL_CARD.md). This one
trades those properties for a richer, multi-label read on tone, at the cost
of a much heavier dependency (transformers + torch) and a model download on
first use. It's used where that weight is acceptable - primarily the
Streamlit demo (see requirements-demo.txt) - and is entirely optional for the
desktop app, which works fully without it.
"""
from __future__ import annotations

MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"

_pipeline_cache = None


class EmotionModelUnavailable(RuntimeError):
    """Raised when transformers/torch aren't installed, or the model can't load."""


def is_available() -> bool:
    """Whether the optional 'transformers' dependency is installed at all.

    Does not guarantee the model can actually be downloaded/loaded (that
    also needs network access the first time) - just that it's worth trying.
    """
    try:
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


def _build_pipeline():
    """Isolated so tests can monkeypatch just this, instead of fighting
    transformers' own lazy-module import machinery."""
    from transformers import pipeline
    return pipeline("text-classification", model=MODEL_NAME, top_k=None)


def _load_pipeline():
    global _pipeline_cache
    if _pipeline_cache is None:
        try:
            _pipeline_cache = _build_pipeline()
        except Exception as error:
            # Deliberately broad: this is a best-effort optional feature, and
            # failures here span more than a plain missing-package ImportError
            # - a mismatched torch/torchvision pair, a blocked model download,
            # an unsupported platform, etc. All of them should degrade to the
            # same "unavailable" message rather than crash the caller.
            raise EmotionModelUnavailable(
                "Multi-emotion analysis needs a working 'transformers' + 'torch' "
                f"install (see requirements-demo.txt) and network access on first "
                f"use to download the model - it isn't available right now: {error}"
            ) from error
    return _pipeline_cache


def score_emotions(text: str) -> dict:
    """Return {emotion_label: probability} for every label the model supports,
    e.g. {'joy': 0.82, 'sadness': 0.04, 'anger': 0.01, ...}."""
    predictions = _load_pipeline()(text)[0]
    return {item["label"]: float(item["score"]) for item in predictions}
