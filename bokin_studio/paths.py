"""Where Bokin Suno Studio keeps things.

- Its own files (the page, Lời Đồng Âm, the version) sit next to the code, or inside the PyInstaller bundle.
- Data (the log, the running app's address, downloaded updates, settings; the Suno accounts and their Chrome
  profiles in suno\\): %APPDATA%\\Bokin\\SunoStudio on Windows, ~/.local/share/Bokin/SunoStudio elsewhere;
  BOKIN_STUDIO_DATA overrides it (tests). The Chrome profiles hold the accounts' Suno sign-ins.
- Results: Music\\Bokin Suno Studio in the user's folder (BOKIN_STUDIO_OUT overrides it): the downloaded songs in
  "Nhac Suno" (unless a folder is chosen), the mastered songs in "Master".
"""

import hashlib
import os
import sys
from pathlib import Path

APP_ID = "bokin-suno-studio"  # what /api/ping answers: the installer and a second start look for it
PORTS = range(8776, 8786)  # Bokin Music uses 8765, Bokin Suno Master 8766-8775


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def root_dir() -> Path:
    """The folder holding loi-dong-am/ and suno/: the repository, or the bundle's own folder (PyInstaller keeps
    them at the same relative place)."""
    if frozen():
        return Path(getattr(sys, "_MEIPASS", package_dir().parent))
    return package_dir().parent


def version() -> str:
    """'1.0.<build>' for an installed app (CI writes version.txt), 'dev' from the source folder."""
    try:
        return (package_dir() / "version.txt").read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def data_dir() -> Path:
    path = os.environ.get("BOKIN_STUDIO_DATA")
    if not path:
        if os.name == "nt":
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
        path = os.path.join(base, "Bokin", "SunoStudio")
    os.makedirs(path, exist_ok=True)
    return Path(path)


def suno_data_dir() -> Path:
    """The Suno downloader's data folder (accounts.json, profiles\\<account>, logs)."""
    return data_dir() / "suno"


def owner() -> str:
    """Who this copy of the app works for (its data folder): another Windows user's copy, on the same shared
    127.0.0.1 ports, answers with a different value and is left alone."""
    return hashlib.sha256(os.path.normcase(str(data_dir())).encode("utf-8")).hexdigest()[:16]


def out_dir() -> Path:
    path = os.environ.get("BOKIN_STUDIO_OUT") or os.path.join(os.path.expanduser("~"), "Music", "Bokin Suno Studio")
    os.makedirs(path, exist_ok=True)
    return Path(path)


def music_dir() -> Path:
    """The default folder for downloaded songs."""
    return out_dir() / "Nhac Suno"


def master_dir() -> Path:
    path = out_dir() / "Master"
    path.mkdir(parents=True, exist_ok=True)
    return path


def updates_dir() -> Path:
    return data_dir() / "updates"


def log_path() -> Path:
    return data_dir() / "app.log"


def settings_path() -> Path:
    return data_dir() / "settings.json"


def running_file() -> Path:
    """The running app's port and per-launch token, readable only by this user (the installer's --close and a
    second start use it to reach the running copy)."""
    return data_dir() / "running.json"
