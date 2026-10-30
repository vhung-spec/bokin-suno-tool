"""The songs downloaded into a folder, as the page lists them: danh-sach.csv (suno/folder.py) read back, with each
song's lyrics file (Title.txt, written by the downloader) when there is one, and its Stems & MIDI folder ("Title -
stems", a row of its own in danh-sach.csv) when they were downloaded.

Folder and file names come from the page (this computer's own user, through the token), but a file is only ever one
listed in that folder's danh-sach.csv, by its bare name: nothing outside the folder is read.
"""

import csv
import io
from pathlib import Path

LIST_NAME = "danh-sach.csv"
AUDIO = {".wav", ".mp3"}
STEMS = "stems"  # (suno/folder.py STEMS)


class LibraryError(Exception):
    pass


def _rows(folder: Path, stems=False):
    """The songs done in the folder's list; with stems=True, the rows of their Stems & MIDI folders instead."""
    path = folder / LIST_NAME
    if not path.is_file():
        return []
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as e:
        raise LibraryError(f"Không đọc được {path}: {e}") from e
    first = text.splitlines()[0] if text.strip() else ""
    delimiter = max((",", ";", "\t"), key=first.count)
    rows = []
    for rec in csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter):
        rec = {k: (v or "") for k, v in rec.items() if k}
        if (rec.get("trang_thai") or "xong").strip().lower() != "xong":
            continue
        name = rec.get("file", "")
        if not name or Path(name).name != name or name in (".", ".."):
            continue
        if (rec.get("dinh_dang", "").strip().lower() == STEMS) != stems:
            continue
        if not stems and Path(name).suffix.lower() not in AUDIO:
            continue
        title = rec.get("ten_bai", "")
        if title[:1] == "'" and title[1:2] in ("=", "+", "-", "@"):
            title = title[1:]  # (suno/folder.py's guard against Excel formulas)
        rows.append({"title": title or Path(name).stem, "file": name, "format": rec.get("dinh_dang", ""),
                     "link": rec.get("link", ""), "at": rec.get("luc", ""), "id": rec.get("id", "")})
    return rows


def songs(folder) -> list:
    """The downloaded songs still in the folder, newest first, each with "lyrics": has a lyrics file."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    stems = {r["id"]: r["file"] for r in _rows(folder, stems=True) if (folder / r["file"]).is_dir()}
    found = []
    for row in _rows(folder):
        audio = folder / row["file"]
        if not audio.is_file():
            continue
        found.append({**row, "lyrics": audio.with_suffix(".txt").is_file(), "size": audio.stat().st_size,
                      "stems": stems.get(row["id"], "")})
    found.sort(key=lambda r: r["at"], reverse=True)
    return found


def song_file(folder, name) -> Path:
    """A song file listed in the folder's danh-sach.csv, or LibraryError."""
    folder = Path(folder)
    if not isinstance(name, str) or Path(name).name != name or name in ("", ".", ".."):
        raise LibraryError("Tên file không hợp lệ")
    if name not in {r["file"] for r in _rows(folder)}:
        raise LibraryError("Bài này không có trong danh-sach.csv của thư mục")
    path = folder / name
    if not path.is_file():
        raise LibraryError(f"Không thấy file {name}")
    return path


def song_row(folder, name) -> dict:
    """The list's row of a song file of the folder (its title, link, id), or LibraryError."""
    song_file(folder, name)
    return next(r for r in _rows(Path(folder)) if r["file"] == name)


def stems_folder(folder, name) -> Path:
    """The Stems & MIDI folder of a song file of the folder, or LibraryError."""
    row = song_row(folder, name)
    path = next((Path(folder) / r["file"] for r in _rows(Path(folder), stems=True) if r["id"] == row["id"]), None)
    if path is None or not path.is_dir():
        raise LibraryError("Bài này chưa có Stems & MIDI trong thư mục")
    return path


def lyrics(folder, name) -> str:
    """The lyrics kept next to a downloaded song ("" if none)."""
    path = song_file(folder, name).with_suffix(".txt")
    try:
        return path.read_text(encoding="utf-8-sig")[:50_000] if path.is_file() else ""
    except (OSError, UnicodeDecodeError) as e:
        raise LibraryError(f"Không đọc được {path.name}: {e}") from e
