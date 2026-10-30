"""The download folder: the audio files and danh-sach.csv, the list of the songs downloaded into it.

A song (in a format) listed in danh-sach.csv as "xong" is not downloaded again, even if its file was deleted or
renamed; delete its line to download it again. A song listed as "loi" (it failed) is tried again on every run, found
by its link, even when the workspace's list is no longer read that far. Files are named after the song title as Suno
shows it; two songs with the same title (Suno makes songs in pairs) get "Title (2).wav". A name (without its
extension) belongs to one song, whatever the format: its lyrics are kept in "Title.txt". Titles come from Suno and
are not trusted: anything Windows or Linux would read as a path, a device name, a command option or a formula in
Excel is taken out.
"""
import csv
import errno
import io
import re
import shutil
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

LIST_NAME = "danh-sach.csv"
STEMS = "stems"  # the dinh_dang of a song's Stems & MIDI in the list; its file is the folder that holds them
UNPACK_MAX = 8_000_000_000  # bytes a stems zip may unpack to
COLUMNS = ("ten_bai", "file", "trang_thai", "ghi_chu", "dinh_dang", "link", "luc", "id")
DONE, FAILED, NOT_MINE = "xong", "loi", "nguoi_khac"  # nguoi_khac: someone else's song, never downloaded
WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)}
NAME_MAX = 80


class FolderError(Exception):
    """danh-sach.csv or the folder cannot be used: the run stops."""


class UnpackError(Exception):
    """A stems zip that cannot be unpacked (broken, too big): that song fails, the run goes on."""


def safe_cell(value):
    """Excel must not run a cell as a formula (song titles are free text)."""
    value = str(value)
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def plain_cell(value):
    """safe_cell undone, for a cell read back."""
    value = str(value or "")
    return value[1:] if value[:1] == "'" and value[1:2] in ("=", "+", "-", "@", "\t", "\r") else value


def safe_filename(title, fallback):
    """A song title -> a file name stem that is safe on Windows and Linux."""
    name = unicodedata.normalize("NFC", title or "")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', " ", name)
    name = re.sub(r"\s+", " ", name).strip().lstrip(". =+-@")  # no hidden file, option or Excel formula
    name = name[:NAME_MAX].rstrip(". ")
    if not name:
        name = fallback
    if name.split(".")[0].strip().lower() in WINDOWS_RESERVED:
        name = "_" + name
    return name


def safe_file_name(name, fallback):
    """A file name from Suno (a zip's entry) -> a safe one. A long one is shortened in the middle: its end (the
    instrument: "Title (Drums).wav") and its extension are kept."""
    stem, dot, ext = (name or "").rpartition(".")
    ext = re.sub(r"[^A-Za-z0-9]", "", ext)[:8] if dot and stem.strip(" .") else ""
    if not ext:
        stem = name or ""
    room = NAME_MAX - (len(ext) + 1 if ext else 0)
    clean = re.sub(r"\s+", " ", re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', " ", unicodedata.normalize("NFC", stem))).strip()
    if len(clean) > room:
        clean = clean[:room - 31].rstrip() + "…" + clean[-30:].lstrip()
    base = safe_filename(clean, fallback)
    return f"{base}.{ext}" if ext else base


def audio_ok(path, fmt):
    """Is the file a WAV / MP3 (not an error page saved under that name)?"""
    path = Path(path)
    try:
        size = path.stat().st_size
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return False
    if size < 1000:
        return False
    if fmt == "wav":
        return head[:4] == b"RIFF" and head[8:12] == b"WAVE"
    return head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0)


def stem_file_ok(path):
    """Is the file one stem (a WAV, an MP3 or a MIDI file), not an error page saved under a stems name?"""
    path = Path(path)
    if audio_ok(path, "wav") or audio_ok(path, "mp3"):
        return True
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"MThd" and path.stat().st_size >= 14
    except OSError:
        return False


def stem_kinds(paths):
    """The kinds of stems among these files: {"wav", "mp3", "midi"}."""
    ext = {".wav": "wav", ".mp3": "mp3", ".mid": "midi", ".midi": "midi"}
    return {ext[Path(p).suffix.lower()] for p in paths if Path(p).suffix.lower() in ext}


def unpack(zip_path, dest, limit=UNPACK_MAX):
    """The files of a zip into `dest`, its folders kept. The names come from Suno and are not trusted: no "..", no
    drive or absolute path, Windows-safe names, nothing outside `dest`, at most `limit` bytes in all, and not more
    than the disk has room for. Returns the files written. Raises UnpackError (a broken or too big zip), OSError (the
    disk is full)."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    written, total = [], 0
    try:
        with zipfile.ZipFile(zip_path) as z:
            declared = sum(i.file_size for i in z.infolist())
            if declared > limit:
                raise UnpackError("File stems giải nén ra quá lớn")
            free = shutil.disk_usage(root).free
            if declared > free:
                raise OSError(errno.ENOSPC, f"No space left on device: the stems need {declared} bytes, {free} free")
            for info in z.infolist():
                if info.is_dir():
                    continue
                parts = [p for p in re.split(r"[\\/]", info.filename) if p.strip() not in ("", ".", "..")]
                parts = ([safe_filename(p, "file") for p in parts[:-1]]
                         + [safe_file_name(p, "file") for p in parts[-1:]])
                if not parts:
                    continue
                target = root.joinpath(*parts)
                if root not in target.resolve().parents:
                    continue
                first, n = target, 2
                while target in written:  # (two names that came out the same once made safe)
                    target = first.with_name(f"{first.stem} ({n}){first.suffix}")
                    n += 1
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(target, "wb") as out:
                    while True:
                        block = src.read(1 << 20)
                        if not block:
                            break
                        total += len(block)
                        if total > limit:
                            raise UnpackError("File stems giải nén ra quá lớn")
                        out.write(block)
                written.append(target)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, RuntimeError, EOFError) as e:
        raise UnpackError(f"File stems nhận được hỏng: {e}") from e
    return written


def _name_base(row):
    """The name (lowercased, without extension) a row's song owns: "title" for "Title.wav", and for its stems
    folder "Title - stems" the same "title" (the song's audio and stems keep one name)."""
    file = row.get("file") or ""
    if (row.get("dinh_dang") or "") == STEMS:
        return re.sub(r" - stems( \(\d+\))?$", "", file, flags=re.I).lower()
    return Path(file).stem.lower()


class Folder:
    def __init__(self, path):
        self.root = Path(path).resolve()
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise FolderError(f"Không tạo được thư mục {self.root}: {e}")
        self.list_path = self.root / LIST_NAME
        self.rows = {}
        if self.list_path.exists():
            raw = self.list_path.read_bytes()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                raise FolderError(f"{self.list_path} không phải UTF-8. Trong Excel: File → Save As → 'CSV UTF-8'")
            first = text.splitlines()[0] if text.strip() else ""
            delimiter = max((",", ";", "\t"), key=first.count)
            for rec in csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter):
                sid, fmt = (rec.get("id") or "").strip().lower(), (rec.get("dinh_dang") or "").strip().lower()
                if sid and fmt:
                    rec = {k: plain_cell(v) for k, v in rec.items() if k}
                    rec["trang_thai"] = (rec.get("trang_thai") or DONE).strip().lower()  # older lists: all done
                    self.rows[(sid, fmt)] = rec
        self.save()  # fails now, before any download, if Excel holds the file open

    def done(self, song_id, fmt):
        return (self.rows.get((song_id, fmt)) or {}).get("trang_thai") == DONE

    def not_mine(self, song_id):
        return any(sid == song_id and r["trang_thai"] == NOT_MINE for (sid, _), r in self.rows.items())

    def failed_before(self, song_id, fmt):
        return (self.rows.get((song_id, fmt)) or {}).get("trang_thai") == FAILED

    def has_audio(self, song_id):
        """Was the song's audio downloaded into this folder (so by the account that owns it)?"""
        return any(sid == song_id and f != STEMS and r["trang_thai"] == DONE for (sid, f), r in self.rows.items())

    def stems_ok(self, song_id):
        """Are the song's stems done, their folder still here? (A folder moved or deleted: they are downloaded
        again.)"""
        row = self.rows.get((song_id, STEMS)) or {}
        return row.get("trang_thai") == DONE and bool(row.get("file")) and (self.root / row["file"]).is_dir()

    def failed(self, fmt):
        """(id, title) of the songs that failed before, to try again."""
        return [(sid, r.get("ten_bai", "")) for (sid, f), r in self.rows.items()
                if f == fmt and r["trang_thai"] == FAILED]

    def target(self, title, song_id, fmt):
        """A new file path for the song: its title, made unique in this folder. The name is not one another song
        uses in any format, nor that of a lyrics file (Title.txt) that is not the song's own."""
        stem = safe_filename(title, f"suno-{song_id[:8]}")
        mine = {_name_base(r) for (sid, _), r in self.rows.items() if sid == song_id and r.get("file")}
        names = {p.name.lower() for p in self.root.iterdir()}
        taken = {_name_base(r) for (sid, _), r in self.rows.items() if sid != song_id and r.get("file")}
        taken |= {Path(r["file"]).name.lower() for r in self.rows.values() if r.get("file")}

        def free(s):
            s = s.lower()
            return (s not in taken and f"{s}.{fmt}" not in names and f"{s}.{fmt}" not in taken
                    and (s in mine or f"{s}.txt" not in names))

        name, n = stem, 2
        while not free(name):
            name, n = f"{stem} ({n})", n + 1
        return self.root / f"{name}.{fmt}"

    def part_path(self, song_id, fmt):
        return self.root / f".{song_id}.{fmt}.part"

    def add(self, song, path, fmt, title):
        self._set(song, fmt, title, DONE, file=Path(path).name)

    def add_failure(self, song, fmt, note):
        self._set(song, fmt, song.title, FAILED, note=note)

    def stems_dir(self, song, title):
        """A new folder for a song's Stems & MIDI, next to its audio file and named after it: "Title - stems". A song
        without its audio here yet gets the name its audio will have (target), so the two stay together."""
        row = self.rows.get((song.id, STEMS)) or {}
        if row.get("file") and not (self.root / row["file"]).exists():
            return self.root / row["file"]
        audio = next((r["file"] for (sid, f), r in self.rows.items() if sid == song.id and f != STEMS
                      and r.get("file")), "")
        stem = Path(audio).stem if audio else self.target(title, song.id, "wav").stem
        taken = {(r.get("file") or "").lower() for (sid, f), r in self.rows.items() if (sid, f) != (song.id, STEMS)}
        name, n = f"{stem} - stems", 2
        while name.lower() in taken or (self.root / name).exists():
            name, n = f"{stem} - stems ({n})", n + 1
        return self.root / name

    def add_stems(self, song, path, title):
        self._set(song, STEMS, title, DONE, file=Path(path).name)

    def add_not_mine(self, song, fmt, note):
        self._set(song, fmt, song.title, NOT_MINE, note=note)

    def _set(self, song, fmt, title, status, file="", note=""):
        self.rows[(song.id, fmt)] = {"ten_bai": title, "file": file, "trang_thai": status, "ghi_chu": note,
                                     "dinh_dang": fmt, "link": song.link,
                                     "luc": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "id": song.id}
        self.save()

    def save(self):
        tmp = self.list_path.with_name(self.list_path.name + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(COLUMNS)
                for rec in self.rows.values():
                    w.writerow([safe_cell(rec.get(c, "")) if c != "id" else rec.get(c, "") for c in COLUMNS])
            tmp.replace(self.list_path)
        except PermissionError:
            raise FolderError(f"Không ghi được {self.list_path}: đóng file này trong Excel rồi chạy lại")
        except OSError as e:
            raise FolderError(f"Không ghi được {self.list_path}: {e}")
