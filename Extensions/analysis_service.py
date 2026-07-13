"""Non-UI business logic shared by the Tkinter app and the Streamlit demo.

Kept separate from Sentiment247.py's widget-building code so the scoring
logic, connectivity check, and crisis-resource threshold can be unit-tested
without a display, and reused outside the desktop app.
"""
from __future__ import annotations

import socket
from dataclasses import dataclass

from Extensions import DepressionScore, PolarityScore

# Below this confidence, the UI should say so rather than presenting every
# result with equal certainty.
LOW_CONFIDENCE_THRESHOLD = 0.65

# Above this confidence, a depressive result is treated as strong enough to
# surface crisis resources alongside it. See MODEL_CARD.md for why this is
# framed as "linguistic markers", never a diagnosis, regardless of confidence.
CRISIS_CONFIDENCE_THRESHOLD = 0.85

CRISIS_RESOURCES = (
    ("988 Suicide & Crisis Lifeline (US)", "Call or text 988"),
    ("Crisis Text Line", "Text HOME to 741741"),
    ("International directory", "findahelpline.com"),
)


def is_connected() -> bool:
    """Check for an active internet connection."""
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=3)
        return True
    except OSError:
        return False


def score_polarity(text: str) -> dict:
    """Run VADER on text, returning positive/neutral/negative as 0-100 ints."""
    result = PolarityScore.sentiment(text)
    return {
        "negative": int(result["neg"] * 100),
        "neutral": int(result["neu"] * 100),
        "positive": int(result["pos"] * 100),
    }


@dataclass(frozen=True)
class DepressionResult:
    is_depressive: bool
    confidence: float  # 0-1, confidence in is_depressive (not always the "depressive" class's own probability)
    low_confidence: bool
    show_crisis_resources: bool


def score_depression(text: str) -> DepressionResult:
    """Run the V2 depression-language pipeline and package the result with
    confidence, a low-confidence flag, and whether to surface crisis resources."""
    is_depressive, confidence = DepressionScore.predict_depressive_with_confidence(text)
    return DepressionResult(
        is_depressive=is_depressive,
        confidence=confidence,
        low_confidence=confidence < LOW_CONFIDENCE_THRESHOLD,
        show_crisis_resources=is_depressive and confidence >= CRISIS_CONFIDENCE_THRESHOLD,
    )
