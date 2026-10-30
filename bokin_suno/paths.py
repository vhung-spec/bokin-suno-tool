"""Where Bokin Suno Master keeps things.

- Its own files (the page, the version) sit next to the code, or inside the PyInstaller bundle.
- Data (the log, the running app's address, downloaded updates): %APPDATA%\\Bokin\\SunoMaster on
  Windows, ~/.local/share/Bokin/SunoMaster elsewhere; BOKIN_SUNO_DATA overrides it (tests).
- Results (one folder per mastered song): Music\\Bokin Suno Master in the user's folder
  (BOKIN_SUNO_OUT overrides it).
"""

import hashlib
import os
import sys
from pathlib import Path

APP_ID = "bokin-suno-master"  # what /api/ping answers: the installer and a second start look for it
PORTS = range(8766, 8776)  # Bokin Music uses 8765


def package_dir() -> Path:
    """The folder of the page and version.txt: inside the bundle when installed (PyInstaller
    keeps the package's data files at the same relative place)."""
    return Path(__file__).resolve().parent


def version() -> str:
    """'1.0.<build>' for an installed app (CI writes version.txt), 'dev' from the source folder."""
    try:
        return (package_dir() / "version.txt").read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def data_dir() -> Path:
    path = os.environ.get("BOKIN_SUNO_DATA")
    if not path:
        if os.name == "nt":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
        path = os.path.join(base, "Bokin", "SunoMaster")
    os.makedirs(path, exist_ok=True)
    return Path(path)


def owner() -> str:
    """Who this copy of the app works for (its data folder): another Windows user's copy, on the
    same shared 127.0.0.1 ports, answers with a different value and is left alone."""
    return hashlib.sha256(os.path.normcase(str(data_dir())).encode("utf-8")).hexdigest()[:16]


def out_dir() -> Path:
    path = os.environ.get("BOKIN_SUNO_OUT") or os.path.join(os.path.expanduser("~"), "Music", "Bokin Suno Master")
    os.makedirs(path, exist_ok=True)
    return Path(path)


def updates_dir() -> Path:
    return data_dir() / "updates"


def log_path() -> Path:
    return data_dir() / "app.log"


def running_file() -> Path:
    """The running app's port and per-launch token, readable only by this user (the installer's
    --close and a second start use it to reach the running copy)."""
    return data_dir() / "running.json"
