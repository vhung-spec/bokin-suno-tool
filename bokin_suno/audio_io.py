"""Reading and writing audio files.

Samples are float64 arrays shaped (samples, channels) in [-1, 1]. WAV, FLAC,
MP3 and OGG go through libsndfile (bundled with the soundfile wheels); other
formats (m4a, aac, opus, ...) are decoded with ffmpeg when it is installed.
"""

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff",
                    ".m4a", ".aac", ".opus", ".webm", ".mp4"}
FORMATS = ("wav", "flac", "mp3")
MP3_RATES = (32000, 44100, 48000)


class AudioError(RuntimeError):
    pass


def load(path: str | Path) -> tuple[np.ndarray, int]:
    """Returns (samples, sample_rate); stereo stays stereo, more channels are
    cut to the first two."""
    path = Path(path)
    if not path.is_file():
        raise AudioError(f"file not found: {path}")
    try:
        data, sr = sf.read(str(path), dtype="float64", always_2d=True)
    except RuntimeError as err:  # LibsndfileError: a format libsndfile cannot read
        data, sr = _load_with_ffmpeg(path, err)
    if data.shape[0] == 0:
        raise AudioError(f"no audio in {path.name}")
    return data[:, :2], sr


def _load_with_ffmpeg(path: Path, err: Exception) -> tuple[np.ndarray, int]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioError(f"cannot read {path.name} ({err}); install ffmpeg "
                         "or convert it to WAV/MP3 first") from err
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "decoded.wav"
        result = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(path),
                                 "-vn", "-c:a", "pcm_f32le", str(wav)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            raise AudioError(f"ffmpeg could not decode {path.name}:\n{result.stderr.strip()}")
        return sf.read(str(wav), dtype="float64", always_2d=True)


def resample(x: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    if sr_from == sr_to:
        return x
    g = math.gcd(sr_from, sr_to)
    return signal.resample_poly(x, sr_to // g, sr_from // g, axis=0)


def _pcm16(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """16-bit samples with TPDF dither (two uniform LSBs), so quiet fades
    decay into soft noise instead of distortion."""
    scaled = x * 32767.0
    scaled += rng.uniform(-0.5, 0.5, x.shape) + rng.uniform(-0.5, 0.5, x.shape)
    return np.clip(np.round(scaled), -32768, 32767).astype(np.int16)


def save(path: str | Path, x: np.ndarray, sr: int, fmt: str = "wav", bits: int = 24) -> Path:
    """Writes x to path (written under a temporary name, then renamed, so a
    failed write never leaves a half file under the real name)."""
    if fmt not in FORMATS:
        raise AudioError(f"unknown format {fmt!r} (use {', '.join(FORMATS)})")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.stem}.partial{path.suffix}")
    x = np.clip(x, -1.0, 1.0 - 2.0 ** -23)
    rng = np.random.default_rng(0)  # same input, same file
    try:
        if fmt == "mp3":
            if sr not in MP3_RATES:
                raise AudioError(f"MP3 needs 32, 44.1 or 48 kHz, not {sr} Hz")
            # compression_level 0 with a constant bitrate is 320 kbps
            sf.write(str(partial), x, sr, format="MP3", subtype="MPEG_LAYER_III",
                     compression_level=0.0, bitrate_mode="CONSTANT")
        elif bits == 16:
            sf.write(str(partial), _pcm16(x, rng), sr, format=fmt.upper(), subtype="PCM_16")
        elif bits == 24:
            sf.write(str(partial), x, sr, format=fmt.upper(), subtype="PCM_24")
        elif bits == 32 and fmt == "wav":
            sf.write(str(partial), x.astype(np.float32), sr, format="WAV", subtype="FLOAT")
        else:
            raise AudioError(f"{fmt.upper()} cannot be written with {bits} bits")
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)
    return path


def audio_files(paths: list[str | Path]) -> list[Path]:
    """Files given on the command line; folders contribute the audio files
    directly inside them."""
    found = []
    for p in map(Path, paths):
        if p.is_dir():
            found += sorted(f for f in p.iterdir()
                            if f.suffix.lower() in AUDIO_EXTENSIONS and not f.name.startswith("."))
        else:
            found.append(p)
    return found
