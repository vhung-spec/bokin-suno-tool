"""What a mastered file says about itself: the song's title, nothing else.

A mastered file is written fresh from samples, so none of the source's tags (artist, album, a comment with a
link to the song on Suno, cover art, the software, dates) comes along. What the encoders add on their own goes
too: the PEAK chunk libsndfile writes into float WAVs (it holds the time of writing), the encoder's name in
FLAC's comment block, any tag an MP3 encoder writes. Then the file gets one tag, the title:

- WAV: a LIST/INFO chunk with INAM (UTF-8, as libsndfile and ffmpeg write it). Windows Explorer reads INFO in the
  ANSI code page, so it shows letters with accents garbled; it reads no "id3 " chunk in a WAV either (both seen on
  Windows in CI), and an INFO in the ANSI code page would be garbled everywhere else
- FLAC: a VORBIS_COMMENT block with TITLE= and no vendor string
- MP3: an ID3v2.3 tag with TIT2 (UTF-16, which Windows Explorer shows)

An MP3 keeps LAME's Info frame: it is part of the sound (the frame count, the encoder's delay for gapless
playback), not a tag. (libsndfile's own way of writing tags is not used: it adds its name to the software tag,
and in MP3s it garbles letters with accents.)
"""

import os
import shutil
import struct
import subprocess
import unicodedata
from pathlib import Path

import soundfile as sf

MAX_TITLE = 250  # characters
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # (Windows: no console flashing up from the app)


def clean_title(text: str | None) -> str:
    """One line of text, without control characters, at most MAX_TITLE characters."""
    if not text:
        return ""
    text = "".join(" " if unicodedata.category(c) in ("Cc", "Zl", "Zp") else c for c in str(text))
    return " ".join(text.split())[:MAX_TITLE].strip()


def source_title(path: str | Path, name: str | None = None) -> str:
    """The song's title: the source's own title tag; without one, `name` (the file's name as it was uploaded)
    or the file name."""
    path = Path(path)
    try:
        with sf.SoundFile(str(path)) as f:
            title = f.title
    except (RuntimeError, OSError):  # a format libsndfile cannot open (m4a, aac, opus): ask ffprobe, if any
        title = _ffprobe_title(path)
    return clean_title(title) or clean_title(name) or clean_title(path.stem) or "untitled"


def _ffprobe_title(path: Path) -> str | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format_tags=title",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                           capture_output=True, timeout=60, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else None


def keep_only_title(path: str | Path, fmt: str, title: str | None) -> None:
    """Rewrites a WAV, FLAC or MP3 file with no tag but `title` (None or "": no tag at all). The sound is
    copied as it is."""
    path = Path(path)
    rewrite = {"wav": _wav, "flac": _flac, "mp3": _mp3}[fmt]
    tmp = path.with_name(path.name + ".tags")
    try:
        with open(path, "rb") as src, open(tmp, "wb") as out:
            rewrite(src, out, os.path.getsize(path), clean_title(title))
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _copy(src, out, n: int) -> None:
    while n > 0:
        block = src.read(min(n, 1 << 20))
        if not block:
            raise ValueError("the file ends early")
        out.write(block)
        n -= len(block)


def _wav(src, out, size: int, title: str) -> None:
    head = src.read(12)
    if head[:4] != b"RIFF" or head[8:] != b"WAVE":
        raise ValueError("not a WAV file")
    out.write(b"RIFF\0\0\0\0WAVE")
    pos = 12
    while pos + 8 <= size:
        src.seek(pos)
        cid, n = struct.unpack("<4sI", src.read(8))
        if cid in (b"fmt ", b"fact", b"data"):  # the sound and how to read it (never PEAK, LIST, id3, bext...)
            out.write(struct.pack("<4sI", cid, n))
            _copy(src, out, n)
            if n & 1:
                out.write(b"\0")
        pos += 8 + n + (n & 1)
    if title:
        text = title.encode("utf-8") + b"\0"
        inam = b"INAM" + struct.pack("<I", len(text)) + text + b"\0" * (len(text) & 1)
        out.write(b"LIST" + struct.pack("<I", 4 + len(inam)) + b"INFO" + inam)
    end = out.tell()
    out.seek(4)
    out.write(struct.pack("<I", end - 8))


def _flac(src, out, size: int, title: str) -> None:
    if src.read(4) != b"fLaC":
        raise ValueError("not a FLAC file")
    keep = []
    while True:
        head = src.read(4)
        if len(head) < 4:
            raise ValueError("the FLAC file ends in its metadata")
        kind, n = head[0] & 0x7F, int.from_bytes(head[1:4], "big")
        body = src.read(n)
        if kind in (0, 3):  # STREAMINFO, SEEKTABLE: how to read and seek the sound
            keep.append((kind, body))
        if head[0] & 0x80:
            break
    if not keep or keep[0][0] != 0:
        raise ValueError("a FLAC file without STREAMINFO")
    if title:
        text = ("TITLE=" + title).encode("utf-8")
        keep.append((4, struct.pack("<III", 0, 1, len(text)) + text))  # no vendor string, one comment
    out.write(b"fLaC")
    for i, (kind, body) in enumerate(keep):
        last = 0x80 if i == len(keep) - 1 else 0
        out.write(bytes([last | kind]) + len(body).to_bytes(3, "big") + body)
    shutil.copyfileobj(src, out, 1 << 20)


def _synchsafe(b: bytes) -> int:
    return (b[0] & 0x7F) << 21 | (b[1] & 0x7F) << 14 | (b[2] & 0x7F) << 7 | (b[3] & 0x7F)


def _id3(title: str) -> bytes:
    """An ID3v2.3 tag with one frame, TIT2 (UTF-16 with its byte order mark)."""
    text = b"\x01\xff\xfe" + title.encode("utf-16-le") + b"\0\0"
    frame = b"TIT2" + struct.pack(">I", len(text)) + b"\0\0" + text
    n = len(frame)
    return b"ID3\x03\x00\x00" + bytes([n >> 21 & 0x7F, n >> 14 & 0x7F, n >> 7 & 0x7F, n & 0x7F]) + frame


def _mp3(src, out, size: int, title: str) -> None:
    start, end = 0, size
    while True:  # ID3v2 tags ahead of the sound
        src.seek(start)
        head = src.read(10)
        if len(head) < 10 or head[:3] != b"ID3":
            break
        start += 10 + _synchsafe(head[6:10]) + (10 if head[3] >= 4 and head[5] & 0x10 else 0)
    while True:  # tags after it: ID3v1, APEv2, an ID3v2 found by its footer
        if end - start >= 128:
            src.seek(end - 128)
            if src.read(3) == b"TAG":
                end -= 128
                continue
        if end - start >= 32:
            src.seek(end - 32)
            footer = src.read(32)
            if footer[:8] == b"APETAGEX":
                n, flags = struct.unpack("<I", footer[12:16])[0], struct.unpack("<I", footer[20:24])[0]
                end -= n + (32 if flags & 0x80000000 else 0)
                continue
            if footer[22:25] == b"3DI":
                end -= 20 + _synchsafe(footer[28:32])
                continue
        break
    if end <= start:
        raise ValueError("an MP3 file without sound")
    if title:
        out.write(_id3(title))
    src.seek(start)
    _copy(src, out, end - start)
