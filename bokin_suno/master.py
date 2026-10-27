"""The mastering chain, its settings and presets.

    load -> (resample) -> low cut -> clean (shimmer, hiss, S, whines)
         -> match a reference / EQ -> mono bass, width -> warmth (saturation)
         -> density (parallel compression) -> glue compression
         -> loudness to target + true-peak limiter -> dither, write

Every stage after loading can be turned off; with everything off and no
loudness target the song comes out as it went in.
"""

import json
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Callable

import numpy as np

from bokin_suno import __version__, audio_io
from bokin_suno.analysis import k_weighted_energy, lufs, lufs_from_energy, measure, \
    true_peak_envelope
from bokin_suno.clean import CleanSettings, clean
from bokin_suno.dynamics import density, glue, limit, limiter_gain
from bokin_suno.tone import EqSettings, apply_curve, eq, lowcut, match_reference, stereo, warmth

LOUDNESS_TOLERANCE = 0.1  # LU
SAMPLE_RATES = (32000, 44100, 48000, 88200, 96000)
MAX_GAIN_DB = 24.0


@dataclass
class Settings:
    target_lufs: float | None = -14.0  # None: keep the song's loudness
    ceiling_db: float = -1.0           # true peak, dBTP
    lowcut_hz: float = 25.0
    clean: CleanSettings = field(default_factory=CleanSettings)
    eq: EqSettings = field(default_factory=EqSettings)
    match: float = 0.7                 # how far to move towards the reference (0-1)
    match_loudness: bool = False       # target the reference's loudness instead
    mono_bass_hz: float = 120.0        # 0: off
    width_db: float = 0.0
    warmth: float = 0.0                # 0-1: gentle saturation of the low mids
    density: float = 0.0               # 0-1: parallel compression
    glue: float = 0.3                  # 0-1
    release_ms: float = 80.0           # limiter release
    sample_rate: int | None = None     # None: keep
    format: str = "wav"
    bits: int = 24
    write_removed: bool = True         # also write what the cleaning took out

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Settings from JSON-like data (numbers may come as strings)."""
        data = dict(data)
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"unknown setting(s): {', '.join(sorted(unknown))}")
        try:
            for key, value in data.items():
                if value is None or key in ("clean", "eq", "format"):
                    continue
                if key in ("sample_rate", "bits"):
                    data[key] = int(value)
                elif key in ("match_loudness", "write_removed"):
                    data[key] = bool(value)
                else:
                    data[key] = float(value)
            for key, kind in (("clean", CleanSettings), ("eq", EqSettings)):
                if isinstance(data.get(key), dict):
                    known = {f.name for f in fields(kind)}
                    if set(data[key]) - known:
                        raise ValueError(f"unknown {key} setting(s): "
                                         f"{', '.join(sorted(set(data[key]) - known))}")
                    data[key] = kind(**{k: float(v) for k, v in data[key].items()})
        except (TypeError, ValueError) as err:
            raise ValueError(f"bad setting: {err}") from err
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)

    def check(self, sr: int | None = None) -> None:
        """Raises ValueError for settings that cannot work, before any
        processing time is spent."""
        if self.format not in audio_io.FORMATS:
            raise ValueError(f"format must be one of {', '.join(audio_io.FORMATS)}")
        if self.format != "mp3" and self.bits not in ((16, 24, 32) if self.format == "wav" else (16, 24)):
            raise ValueError(f"{self.format.upper()} cannot be written with {self.bits} bits")
        if self.target_lufs is not None and not -40 <= self.target_lufs <= -3:
            raise ValueError("target loudness must be between -40 and -3 LUFS")
        if not -12 <= self.ceiling_db <= 0:
            raise ValueError("ceiling must be between -12 and 0 dBTP")
        ranges = {"match": (0, 1), "glue": (0, 1), "warmth": (0, 1), "density": (0, 1),
                  "lowcut_hz": (0, 200), "mono_bass_hz": (0, 300),
                  "width_db": (-12, 12), "release_ms": (10, 2000)}
        values = {k: getattr(self, k) for k in ranges}
        ranges.update({f"clean.{k}": (0, 1) for k in asdict(self.clean)})
        values.update({f"clean.{k}": v for k, v in asdict(self.clean).items()})
        ranges.update({f"eq.{k}": (-12, 12) for k in asdict(self.eq)})
        values.update({f"eq.{k}": v for k, v in asdict(self.eq).items()})
        for key, (lo, hi) in ranges.items():
            if not lo <= values[key] <= hi:
                raise ValueError(f"{key} must be between {lo} and {hi}")
        if self.sample_rate is not None and self.sample_rate not in SAMPLE_RATES:
            raise ValueError(f"sample rate must be one of {', '.join(map(str, SAMPLE_RATES))}")
        out_sr = self.sample_rate or sr
        if self.format == "mp3" and out_sr and out_sr not in audio_io.MP3_RATES:
            raise ValueError(f"MP3 needs 32, 44.1 or 48 kHz, not {out_sr} Hz: set the sample rate")


PRESETS = {
    # Spotify, YouTube, Apple Music and TikTok turn louder songs down to about
    # -14 LUFS: mastering louder only costs dynamics there.
    "streaming": {"target_lufs": -14.0, "ceiling_db": -1.0},
    "loud": {"target_lufs": -10.0, "ceiling_db": -1.0, "glue": 0.5},
    "gentle": {"target_lufs": -16.0, "ceiling_db": -1.5, "glue": 0.15,
               "clean": {"shimmer": 0.35, "dehiss": 0.0, "deess": 0.0, "dewhine": 0.5}},
    "clean_only": {"target_lufs": None, "glue": 0.0, "mono_bass_hz": 0.0},
    # Bossa nova, jazz, Christmas jazz: fuller and clearer, dynamics kept.
    # Body and warmth thicken guitar, piano, upright bass and voice; presence
    # and air bring them forward; parallel compression lifts the quiet details
    # (brushes, breaths, tails). Lighter shimmer removal spares brushes and
    # bells; a slower limiter release keeps the upright bass clean.
    "jazz": {"target_lufs": -14.0, "ceiling_db": -1.0, "glue": 0.15, "warmth": 0.35, "density": 0.35,
             "mono_bass_hz": 100.0, "release_ms": 150.0,
             "clean": {"shimmer": 0.4, "dehiss": 0.0, "deess": 0.0, "dewhine": 0.5},
             "eq": {"body": 2.0, "presence": 1.5, "air": 1.0}},
}


def preset(name: str, **overrides) -> Settings:
    """A preset's settings; `clean` and `eq` overrides may name only some of
    their fields."""
    if name not in PRESETS:
        raise ValueError(f"unknown preset {name!r} (use {', '.join(PRESETS)})")
    data = {**PRESETS[name], **overrides}
    for key, kind in (("clean", CleanSettings), ("eq", EqSettings)):
        data[key] = {**asdict(kind()), **PRESETS[name].get(key, {}), **overrides.get(key, {})}
    return Settings.from_dict(data)


@dataclass
class Result:
    output: Path
    removed: Path | None
    report: dict


Progress = Callable[[str, float], None]


def process(x: np.ndarray, sr: int, settings: Settings,
            reference: tuple[np.ndarray, int] | None = None,
            progress: Progress | None = None) -> tuple[np.ndarray, np.ndarray | None, dict]:
    """Masters x; returns (mastered, removed by cleaning or None, report)."""
    def step(name: str, fraction: float = 0.0):
        if progress:
            progress(name, fraction)

    settings.check(sr)
    if len(x) < sr // 2:
        raise ValueError("the song is shorter than half a second")
    t0 = time.time()
    report: dict = {"stages": {}, "notes": []}
    if settings.sample_rate and settings.sample_rate != sr:
        step("resample")
        x = audio_io.resample(x, sr, settings.sample_rate)
        sr = settings.sample_rate
    report["input"] = measure(x, sr)
    if report["input"]["clipped_samples"] > 100:
        report["notes"].append("clipped_input")

    y = lowcut(x, sr, settings.lowcut_hz)

    removed = None
    if settings.clean.active():
        step("clean", 0.0)
        cleaned, stats = clean(y, sr, settings.clean, progress=lambda f: step("clean", f))
        removed = y - cleaned
        y = cleaned
        report["stages"]["clean"] = stats

    target = settings.target_lufs
    if reference is not None:
        step("match")
        ref, ref_sr = reference
        match = match_reference(y, sr, ref, ref_sr, settings.match)
        y = apply_curve(y, sr, match.freqs, match.curve_db)
        report["stages"]["match"] = match.summary()
        width_db = settings.width_db + match.width_db
        if settings.match_loudness:
            target = round(lufs(ref, ref_sr), 1)
            report["stages"]["match"]["reference_lufs"] = target
    else:
        width_db = settings.width_db

    step("tone")
    y = eq(y, sr, settings.eq)
    y = stereo(y, sr, settings.mono_bass_hz, width_db)
    if settings.warmth > 0:
        y, report["stages"]["warmth"] = warmth(y, sr, settings.warmth)
    if settings.density > 0:
        y, report["stages"]["density"] = density(y, sr, settings.density)

    step("glue")
    y, report["stages"]["glue"] = glue(y, sr, settings.glue)

    step("loudness")
    y, report["stages"]["loudness"] = _loudness(y, sr, target, settings)
    report["output"] = measure(y, sr, report["stages"]["loudness"].pop("true_peak_db"))
    if target is not None and report["output"]["lufs"] < target - 0.5:
        report["notes"].append("target_not_reached")
    report["seconds_taken"] = round(time.time() - t0, 1)
    return y, removed, report


def _loudness(y: np.ndarray, sr: int, target: float | None, settings: Settings) -> tuple[np.ndarray, dict]:
    """Gain to the target loudness, limited to the ceiling. The limiter takes
    some loudness off, so the gain is raised until the result is on target.

    Trial gains are judged without rendering: the limiter's gain moves
    slowly next to the K-weighting filter, so the loudness of x * g is that
    of x's K-weighted energy times g^2. One real measurement corrects the
    small error that remains."""
    before = lufs(y, sr)
    envelope = true_peak_envelope(y)
    if target is None or not np.isfinite(before):
        out, stats = limit(y, sr, settings.ceiling_db, envelope=envelope,
                           release_ms=settings.release_ms)
        return out, {"gain_db": 0.0, **stats}
    energy = k_weighted_energy(y, sr)

    def trial(gain_db: float) -> float:
        gain = 10 ** (gain_db / 20)
        g = limiter_gain(envelope * gain, sr, settings.ceiling_db, release_ms=settings.release_ms)
        return lufs_from_energy(energy * (gain * g) ** 2, sr)

    def settle(gain_db: float) -> float:
        for _ in range(8):
            miss = target - trial(gain_db)
            if abs(miss) <= LOUDNESS_TOLERANCE / 2 or gain_db >= MAX_GAIN_DB:
                break
            gain_db = min(MAX_GAIN_DB, gain_db + miss)
        return gain_db

    gain_db = settle(min(MAX_GAIN_DB, target - before))
    out, stats = limit(y, sr, settings.ceiling_db, gain=10 ** (gain_db / 20),
                       envelope=envelope, release_ms=settings.release_ms)
    miss = target - lufs(out, sr)
    if abs(miss) > LOUDNESS_TOLERANCE and gain_db < MAX_GAIN_DB:
        gain_db = min(MAX_GAIN_DB, gain_db + miss)
        out, stats = limit(y, sr, settings.ceiling_db, gain=10 ** (gain_db / 20),
                           envelope=envelope, release_ms=settings.release_ms)
    return out, {"gain_db": round(gain_db, 2), **stats}


def output_name(source: Path, settings: Settings) -> str:
    return f"{source.stem}_master.{settings.format}"


def master_file(source: str | Path, out_dir: str | Path, settings: Settings,
                reference: str | Path | None = None,
                progress: Progress | None = None) -> Result:
    """Masters one file into out_dir: <name>_master.<fmt>, <name>_removed.wav
    (when cleaning ran) and <name>_report.json."""
    source, out_dir = Path(source), Path(out_dir)
    settings.check()
    if progress:
        progress("load", 0.0)
    x, sr = audio_io.load(source)
    ref = audio_io.load(reference) if reference else None
    y, removed, report = process(x, sr, settings, ref, progress)
    sr_out = settings.sample_rate or sr
    if progress:
        progress("write", 0.0)
    output = audio_io.save(out_dir / output_name(source, settings), y, sr_out,
                           settings.format, settings.bits)
    removed_path = None
    if removed is not None and settings.write_removed:
        removed_path = audio_io.save(out_dir / f"{source.stem}_removed.wav", removed, sr_out, "wav", 24)
    if settings.format == "mp3":  # what listeners get: the decoded MP3
        decoded, _ = audio_io.load(output)
        report["output"] = measure(decoded, sr_out)
        if report["output"]["true_peak_db"] > -0.1:
            report["notes"].append("mp3_overs")
    report.update({
        "version": __version__,
        "source": source.name,
        "reference": Path(reference).name if reference else None,
        "output_file": output.name,
        "removed_file": removed_path.name if removed_path else None,
        "settings": settings.to_dict(),
    })
    (out_dir / f"{source.stem}_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                         encoding="utf-8")
    return Result(output, removed_path, report)
