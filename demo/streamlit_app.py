"""Streamlit web demo for Feelz.

Mirrors the desktop app's Polarity and Depression-language modes (plus an
optional multi-emotion breakdown) as a page anyone can open in a browser -
no Python install, no Tkinter, no cloning the repo. See the README's "Try it
online" section for one-click deploy instructions (Streamlit Community
Cloud / Hugging Face Spaces).

Run locally:
    pip install -r requirements.txt -r requirements-demo.txt
    streamlit run demo/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from Extensions import analysis_service, emotion_model

st.set_page_config(page_title="Feelz - mood & sentiment demo", page_icon="🙂", layout="centered")

st.title("Feelz")
st.caption(
    "A mood and sentiment workspace. This demo runs the same models as the "
    "desktop app - see [MODEL_CARD.md](https://github.com/korbirayen/Feelz/blob/main/MODEL_CARD.md) "
    "for what they do and don't measure, and "
    "[PRIVACY.md](https://github.com/korbirayen/Feelz/blob/main/PRIVACY.md) for what this page sends anywhere."
)

text = st.text_area(
    "Type or paste some text",
    height=150,
    placeholder="Type a few sentences here and press Analyze to check the tone...",
)

analyze = st.button("Analyze", type="primary")

if analyze:
    if not text.strip():
        st.error("Type something first.")
        st.stop()

    st.divider()

    # ---- Polarity ----
    st.subheader("Polarity")
    scores = analysis_service.score_polarity(text)
    cols = st.columns(3)
    cols[0].metric("Positive", f"{scores['positive']}%")
    cols[1].metric("Neutral", f"{scores['neutral']}%")
    cols[2].metric("Negative", f"{scores['negative']}%")
    st.caption("Positive / neutral / negative shares from VADER's sentiment score.")

    # ---- Depression-language markers ----
    st.subheader("Language patterns")
    result = analysis_service.score_depression(text)
    confidence_pct = round(result.confidence * 100)
    if result.is_depressive:
        st.error(f"Depressive tone detected ({confidence_pct}% confidence)")
    else:
        st.success(f"No strong depressive tone detected ({confidence_pct}% confidence)")
    if result.low_confidence:
        st.caption("Low confidence - take this one with a grain of salt.")
    st.caption(
        "A word-pattern signal, not a diagnosis - see MODEL_CARD.md for why a "
        "model that's very good at this narrow task isn't the same thing as a "
        "clinical screening tool."
    )

    if result.show_crisis_resources:
        with st.container(border=True):
            st.markdown("**If this feels urgent, you don't have to handle it alone:**")
            for name, action in analysis_service.CRISIS_RESOURCES:
                st.markdown(f"- **{name}** - {action}")

    # ---- Optional multi-emotion breakdown ----
    st.subheader("Emotions (optional)")
    if not emotion_model.is_available():
        st.info(
            "Multi-emotion analysis needs the optional 'transformers' + 'torch' "
            "packages from requirements-demo.txt - not installed here."
        )
    else:
        with st.spinner("Loading the emotion model (first run downloads it)..."):
            emotions: dict | None
            try:
                emotions = emotion_model.score_emotions(text)
            except emotion_model.EmotionModelUnavailable as error:
                st.info(str(error))
                emotions = None
        if emotions:
            ranked = sorted(emotions.items(), key=lambda item: item[1], reverse=True)
            st.bar_chart({label: score for label, score in ranked})

st.divider()
st.caption(
    "Everything above runs the same way it does in the desktop app - VADER and "
    "the TF-IDF + Logistic Regression pipeline run locally in this server "
    "process; nothing about your text is stored. See PRIVACY.md for the full picture."
)
