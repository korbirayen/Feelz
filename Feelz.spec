# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a standalone Feelz build (onedir - see README's
"Package as a standalone build" section for why not onefile).

Build:
    pip install -r requirements.txt -r requirements-dev.txt pyinstaller
    pyinstaller Feelz.spec

Produces dist/Feelz/Feelz.exe. The whole dist/Feelz/ folder is the
distributable - it's self-contained (images/, Extensions/Models/*.pickle,
and the NLTK data VADER/DepressionScore need are all bundled in), and a
fresh Data/ folder (theme + local mood history) is created next to the exe
on first run. See Extensions/runtime_paths.py for how the app finds these
once frozen.
"""
from pathlib import Path

import nltk

block_cipher = None


def _nltk_resource_path(resource_id):
    """Resolve one NLTK resource id (e.g. 'tokenizers/punkt') to a real
    filesystem path, wherever this machine's nltk_data happens to live -
    the build shouldn't hardcode a path specific to whoever runs it."""
    found = nltk.data.find(resource_id)
    return Path(found.path if hasattr(found, "path") else str(found))


nltk_datas = [
    (str(_nltk_resource_path("tokenizers/punkt")), "nltk_data/tokenizers/punkt"),
    (str(_nltk_resource_path("tokenizers/punkt_tab")), "nltk_data/tokenizers/punkt_tab"),
    (str(_nltk_resource_path("corpora/stopwords")), "nltk_data/corpora/stopwords"),
]

# vader_lexicon ships (and is read by nltk) as a zip file, not an extracted folder.
vader_zip = _nltk_resource_path("sentiment/vader_lexicon.zip")
nltk_datas.append((str(vader_zip), "nltk_data/sentiment"))

a = Analysis(
    ['Sentiment247.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('images', 'images'),
        ('Extensions/Models', 'Extensions/Models'),
        *nltk_datas,
    ],
    hiddenimports=[
        'sklearn.utils._typedefs',
        'sklearn.utils._heap',
        'sklearn.utils._sorting',
        'sklearn.utils._vector_sentinel',
        'sklearn.neighbors._partition_nodes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Feelz itself never imports these - they only show up if you build from
    # an environment that has them installed for unrelated projects (e.g. a
    # shared global site-packages). Excluding them explicitly keeps the build
    # from silently ballooning to a gigabyte-plus of irrelevant packages;
    # building from a clean venv with only requirements.txt installed avoids
    # needing this list at all.
    excludes=[
        'torch', 'torchvision', 'transformers', 'sentence_transformers',
        'streamlit', 'gradio', 'yt_dlp', 'websockets', 'curl_cffi',
        'Cryptodome', 'Crypto', 'mutagen', 'cv2', 'faiss_cpu', 'psycopg2',
        'IPython', 'Pythonwin', 'secretstorage',
    ],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Feelz',
    icon='images/logo_img.ico',
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='Feelz',
)
