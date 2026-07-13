# Feelz

[![CI](https://github.com/korbirayen/Feelz/actions/workflows/ci.yml/badge.svg)](https://github.com/korbirayen/Feelz/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

Feelz is a small desktop mood and sentiment workspace that I refactored from
the original Sentiment247 project. It still does the same core jobs, but the
branding, launch flow, and a lot of the internals have been cleaned up and
extended so it feels like a real product instead of a class assignment.

It can check typed text, read text files, pull text from images, record and
transcribe speech from your microphone, and read public X (Twitter) post
URLs - all through the same sentiment/depression-language models - plus keep
a local trend of your results over time and run all of it in bulk over a
batch of entries.

<!--
  TODO: drop a screenshot in as docs/screenshots/text-dark.png and uncomment:
  ![Feelz - text mode, dark theme](docs/screenshots/text-dark.png)
  (Text > Polarity, dark theme, after submitting something like "Had an
  amazing day today, I feel grateful and full of energy!" - 53% positive.)
-->

## Features

- **Four input modes**: typed text, uploaded `.txt`/image files (OCR via
  Google Vision), voice recording (free Google Web Speech transcription),
  and public X/Twitter post URLs (no API keys needed).
- **Two analysis modes**: VADER-based polarity (positive/neutral/negative)
  and a depression-language classifier, shown with a confidence percentage
  rather than a bare yes/no - see [MODEL_CARD.md](MODEL_CARD.md) for exactly
  what that model does and doesn't measure.
- **Crisis-aware, on purpose**: a high-confidence depressive result surfaces
  calm, non-intrusive crisis-line resources instead of just a verdict.
- **Local mood history**: every analysis is logged to a local-only database
  and plotted as a trend line in the History tab - nothing here ever leaves
  your device (see [PRIVACY.md](PRIVACY.md)).
- **Batch mode**: paste or upload many entries at once and get aggregate
  polarity/depression stats plus a per-row breakdown.
- **Light/dark themes**, keyboard shortcuts (`Alt+1`-`7` to jump between
  tabs, `Ctrl+Enter` to submit), and colors checked against WCAG contrast
  guidelines.
- **Try it without installing anything**: a [Streamlit web demo](#try-it-online)
  mirrors the polarity/depression modes, plus an optional multi-emotion
  breakdown.

## What You Need

Everything works out of the box except image OCR:

- Set `GOOGLE_APPLICATION_CREDENTIALS` to your Google Vision service account JSON path if you want OCR to use your own project credentials.
- Social post lookups use X/Twitter's public oEmbed endpoint, so no developer account or API keys are needed - just a public post URL.
- Voice input uses your default microphone and the free Google Web Speech API for transcription (no account needed, but it does need an internet connection).

If you want to make the app fully yours, replace the images in `images/` and swap out the legacy model files when you are ready.

## Start The App

Run `start_feelz.bat` from the project root. That script calls `start_feelz.py`, which checks the Python packages, downloads the NLTK data the app needs, and then launches the desktop app.

## Try It Online

A [Streamlit](https://streamlit.io) demo (`demo/streamlit_app.py`) mirrors the
polarity and depression-language modes in a browser - nothing to install, no
Tkinter, no cloning the repo:

```bash
pip install -r requirements.txt -r requirements-demo.txt
streamlit run demo/streamlit_app.py
```

It also has an optional multi-emotion breakdown (joy/sadness/anger/fear/...)
via a small HuggingFace transformer - see `Extensions/emotion_model.py`. That
part is heavy (`transformers` + `torch`) and downloads a model on first use,
which is exactly why it's kept out of the desktop app's own dependencies and
only wired into this demo.

To put this behind a real URL, both [Streamlit Community Cloud](https://streamlit.io/cloud)
and [Hugging Face Spaces](https://huggingface.co/spaces) offer free hosting -
point either one at `demo/streamlit_app.py` with `requirements.txt` +
`requirements-demo.txt` as the dependency files.

## Package As A Standalone Build

`Feelz.spec` builds a self-contained folder (`dist/Feelz/Feelz.exe` plus
everything it needs alongside it) with [PyInstaller](https://pyinstaller.org),
so it can be shared as a "download and double-click" build with no Python
install required:

```bash
pip install -r requirements.txt -r requirements-dev.txt pyinstaller
pyinstaller Feelz.spec
```

Build this from a **clean virtual environment that only has `requirements.txt`
installed**. PyInstaller bundles whatever's importable in the environment it
runs in - building from a shared/global Python install that also has
unrelated heavy packages lying around (torch, streamlit, etc.) can balloon
the output to a gigabyte-plus of stuff Feelz never uses. `Feelz.spec`
explicitly excludes the usual suspects, but a clean venv avoids the problem
entirely and builds a much smaller, faster-to-start folder.

The whole `dist/Feelz/` folder is the distributable - `images/`, the trained
model pickles, and the NLTK data VADER/the depression classifier need are all
bundled in, and a fresh `Data/` folder (theme + local mood history) is
created next to the exe the first time it runs. See
`Extensions/runtime_paths.py` for how the app tells a packaged build apart
from running out of the source checkout.

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest              # unit tests for every non-UI module
ruff check .         # lint
mypy .               # type-check (the legacy Tkinter/hand-rolled classifier
                     # files are intentionally excluded - see pyproject.toml)
```

CI (`.github/workflows/ci.yml`) runs all three on every push/PR, plus a
second job that reproduces the depression-model evaluation end to end and
uploads the resulting metrics/confusion matrices as a build artifact.

## The Depression-Language Model

See [MODEL_CARD.md](MODEL_CARD.md) for the full writeup: two model versions
kept side by side on purpose (a weak hand-rolled baseline vs. the shipped
TF-IDF + Logistic Regression pipeline), exact metrics on a reproducible
held-out split, and - more importantly - what a 99.2%-accuracy number here
does and doesn't tell you about real-world use.

Reproduce it yourself:

```bash
pip install -r requirements.txt -r requirements-eval.txt
python evaluate_depression_model.py
```

## Privacy

See [PRIVACY.md](PRIVACY.md) for exactly what stays on your device (VADER,
the depression classifier, your theme + mood history) versus what's sent to
a third party and only when you use that specific feature (Google Vision for
image OCR, Google's Web Speech API for voice, X/Twitter's public oEmbed
endpoint for post lookups).

## A Small Note

The project still has some original structure inside it, because I kept the working pieces in place while modernizing the name and the startup path. That makes it easier to keep the app stable while you keep iterating on the design.
