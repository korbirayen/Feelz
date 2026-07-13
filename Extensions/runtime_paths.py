"""Resolves the app's root directories for both "running from source" and
"running from a PyInstaller onedir build".

A frozen module's __file__ points inside PyInstaller's bundled archive, not
a real directory on disk - so Path(__file__).resolve().parent(.parent)
tricks used elsewhere in this codebase to find images/, Extensions/Models/,
or Data/ silently point at a path that doesn't exist once frozen. This is
the one place that distinction is made, so DepressionScore.py,
history_store.py, and Sentiment247.py can all just ask "where do my
bundled/writable files live" without duplicating the frozen check.
"""
from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Directory for writable app data (Data/ - theme + local mood history) -
    the frozen exe's own directory when packaged, the repo root when running
    from source. Deliberately next to the exe itself even when bundled_root()
    below resolves to an _internal/ subfolder, so user data doesn't end up
    nested inside a directory named for internal/bundled files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundled_root() -> Path:
    """Directory holding bundled read-only assets: images/, Extensions/Models/,
    nltk_data/. PyInstaller 6+ nests these under an _internal/ folder next to
    the exe by default (older layouts, or building with
    `--contents-directory .`, put them directly next to the exe instead) -
    check both so this doesn't silently break across PyInstaller versions."""
    root = app_root()
    if not getattr(sys, "frozen", False):
        return root
    internal = root / "_internal"
    return internal if internal.exists() else root


def ensure_nltk_data_path() -> None:
    """Point nltk at the bundled nltk_data/ folder when frozen (see
    Feelz.spec), before anything imports nltk.corpus/nltk.sentiment - some of
    that (PolarityScore's SentimentIntensityAnalyzer) loads its data at
    import time, so this must run before those imports, not just before
    App.__init__. A no-op when running from source or when unbundled,
    since the target machine's own nltk_data (or start_feelz.py's download
    step) already covers that case.
    """
    if not getattr(sys, "frozen", False):
        return
    import nltk

    bundled = bundled_root() / "nltk_data"
    if bundled.exists() and str(bundled) not in nltk.data.path:
        nltk.data.path.append(str(bundled))
