import json
import shutil
import struct
import subprocess
import sys
import warnings

import numpy as np
import pytest
import soundfile as sf

from bokin_suno import audio_io, tags
from bokin_suno.master import master_file, preset
from tests.conftest import SR, music

TITLE = "Đêm Thánh Vô Cùng (Bossa) – bản 2"
OTHERS = {"artist": "Ca sĩ Suno", "album": "Album Giáng sinh", "comment": "made with suno.com/song/abc-123",
          "software": "Suno", "date": "2026-11-04", "genre": "Bossa nova"}


def tagged_source(path, title=TITLE):
    """A WAV with every tag libsndfile writes (it adds its own name to the software tag)."""
    with sf.SoundFile(str(path), "w", SR, 2, "PCM_24", format="WAV") as f:
        if title:
            f.title = title
        for key, value in OTHERS.items():
            setattr(f, key, value)
        f.write(music(3.0))
    return path


def riff_chunks(path):
    b = path.read_bytes()
    out, i = [], 12
    while i + 8 <= len(b):
        cid, n = struct.unpack("<4sI", b[i:i + 8])
        out.append(cid)
        i += 8 + n + (n & 1)
    return out


def flac_blocks(path):
    b = path.read_bytes()
    out, i = [], 4
    while True:
        head, n = b[i], int.from_bytes(b[i + 1:i + 4], "big")
        out.append((head & 0x7F, b[i + 4:i + 4 + n]))
        i += 4 + n
        if head & 0x80:
            return out


def id3_frames(path):
    b = path.read_bytes()
    assert b[:5] == b"ID3\x03\x00"
    end = 10 + tags._synchsafe(b[6:10])
    out, i = [], 10
    while i + 10 <= end and b[i:i + 4] != b"\0\0\0\0":
        n = struct.unpack(">I", b[i + 4:i + 8])[0]
        out.append((b[i:i + 4], b[i + 10:i + 10 + n]))
        i += 10 + n
    return out


def assert_only_title(path, fmt, title=TITLE):
    with sf.SoundFile(str(path)) as f:
        assert f.copy_metadata() == {"title": title}
    raw = path.read_bytes()
    for value in list(OTHERS.values()) + ["libsndfile", "Lavf"]:
        for enc in ("utf-8", "utf-16-le"):
            assert value.encode(enc) not in raw, (fmt, value)
    if fmt == "wav":
        assert riff_chunks(path)[-1] == b"LIST" and set(riff_chunks(path)) <= {b"fmt ", b"fact", b"data", b"LIST"}
    elif fmt == "flac":
        blocks = flac_blocks(path)
        assert [k for k, _ in blocks] == [0, 4]
        text = ("TITLE=" + title).encode()
        assert blocks[1][1] == struct.pack("<III", 0, 1, len(text)) + text  # no vendor string, one comment
    else:
        assert id3_frames(path) == [(b"TIT2", b"\x01\xff\xfe" + title.encode("utf-16-le") + b"\0\0")]
        assert raw[-128:-125] != b"TAG" and b"APETAGEX" not in raw[-64:]


@pytest.mark.parametrize("fmt,bits", [("wav", 24), ("wav", 32), ("flac", 24), ("mp3", 24)])
def test_a_master_carries_the_title_and_nothing_else(tmp_path, fmt, bits):
    source = tagged_source(tmp_path / "Bài gốc.wav")
    result = master_file(source, tmp_path / "out", preset("bossa", format=fmt, bits=bits))
    assert_only_title(result.output, fmt)
    assert result.report["title"] == TITLE
    assert riff_chunks(result.removed) == [b"fmt ", b"data"]  # the removed part: no tag at all


def test_without_a_title_tag_the_name_as_uploaded_or_the_file_name(tmp_path):
    source = tagged_source(tmp_path / "Silent Night _Bossa.wav", title=None)
    plain = master_file(source, tmp_path / "a", preset("streaming"))
    assert_only_title(plain.output, "wav", "Silent Night _Bossa")
    named = master_file(source, tmp_path / "b", preset("streaming"), name="Silent Night (Bossa)\n")
    assert_only_title(named.output, "wav", "Silent Night (Bossa)")


@pytest.mark.parametrize("fmt,subtype", [("wav", "FLOAT"), ("flac", "PCM_24"), ("mp3", "MPEG_LAYER_III")])
def test_tags_an_encoder_wrote_go_and_the_sound_stays(tmp_path, fmt, subtype):
    # libsndfile writes tags when asked: a PEAK chunk (the time of writing) and LIST in WAV, a comment block with
    # the encoder's name in FLAC, ID3v2 and ID3v1 (LAME) in MP3
    path = tmp_path / f"tagged.{fmt}"
    with sf.SoundFile(str(path), "w", SR, 2, subtype, format=fmt.upper()) as f:
        f.title, f.artist, f.comment = "x", OTHERS["artist"], OTHERS["comment"]
        f.write(music(2.0))
    before, _ = sf.read(str(path))
    tags.keep_only_title(path, fmt, TITLE)
    assert_only_title(path, fmt)
    after, _ = sf.read(str(path))
    np.testing.assert_array_equal(after, before)
    tags.keep_only_title(path, fmt, None)
    with sf.SoundFile(str(path)) as f:
        assert f.copy_metadata() == {}
    np.testing.assert_array_equal(sf.read(str(path))[0], before)


def test_clean_title():
    assert tags.clean_title(" Silent\tNight\r\n(Bossa)\x00 ") == "Silent Night (Bossa)"
    assert len(tags.clean_title("a" * 1000)) == tags.MAX_TITLE
    assert tags.clean_title(None) == ""


@pytest.mark.skipif(not shutil.which("ffprobe") or not shutil.which("ffmpeg"), reason="needs ffmpeg")
def test_title_of_a_format_libsndfile_cannot_read(tmp_path):
    src = tagged_source(tmp_path / "a.wav")
    m4a = tmp_path / "a.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-metadata", f"title={TITLE}", str(m4a)], check=True)
    assert tags.source_title(m4a) == TITLE


@pytest.mark.skipif(sys.platform != "win32", reason="what Windows Explorer shows")
def test_windows_shows_the_title(tmp_path, capsys):
    """Explorer's Title column (System.Title) for each format, with a title in plain letters and one with
    Vietnamese letters."""
    x = music(2.0)
    plain = "Silent Night (Bossa)"
    files = {}
    for fmt in ("wav", "flac", "mp3"):
        for kind, title in (("plain", plain), ("vi", TITLE)):
            name = f"{kind}.{fmt}"
            audio_io.save(tmp_path / name, x, SR, fmt, 24, title=title)
            files[name] = title
    out = tmp_path / "shown.txt"
    script = (f"$f = (New-Object -ComObject Shell.Application).Namespace('{tmp_path}'); $r = @(); "
              + "".join(f"$r += [string]$f.ParseName('{n}').ExtendedProperty('System.Title'); " for n in files)
              + f"[IO.File]::WriteAllLines('{out}', $r, (New-Object Text.UTF8Encoding $false))")
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, timeout=120)
    shown = dict(zip(files, out.read_text(encoding="utf-8").splitlines(), strict=True))
    with capsys.disabled():  # a notice on the CI run: what Explorer shows
        print("::notice title=Windows Explorer titles::" + json.dumps(shown, ensure_ascii=True))
    if not shown.get("plain.mp3"):
        pytest.skip(f"this Windows shows no audio titles: {shown}")
    for name, title in files.items():
        if name == "vi.wav" and shown[name] != title:  # (RIFF INFO has no character set: noted, not failed)
            warnings.warn(f"Windows Explorer shows the WAV title {title!r} as {shown[name]!r}", stacklevel=2)
            continue
        assert shown[name] == title, (name, shown)
