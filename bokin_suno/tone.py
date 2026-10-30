"""Tone and stereo: low cut, EQ, warmth (saturation), matching a reference
song, mono bass, width."""

from dataclasses import dataclass

import numpy as np
from scipy import signal

from bokin_suno.analysis import average_spectrum, side_mid_ratio

MATCH_TAPS = 8191         # linear-phase FIR, ~6 Hz resolution at 48 kHz
MATCH_MAX_CUT_DB = 9.0
MATCH_MAX_BOOST_DB = 6.0
MATCH_MAX_WIDTH_DB = 3.0
WARMTH_BAND_HZ = (100.0, 1200.0)


def lowcut(x: np.ndarray, sr: int, hz: float) -> np.ndarray:
    """Removes rumble and DC (zero phase, so the kick keeps its shape)."""
    if not hz:
        return x
    sos = signal.butter(2, hz, "highpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


# -- EQ (RBJ audio EQ cookbook biquads) -------------------------------------

def _biquad(kind: str, f0: float, gain_db: float, q: float, sr: int) -> np.ndarray:
    a = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / sr
    cos, sin = np.cos(w0), np.sin(w0)
    if kind == "peak":
        alpha = sin / (2 * q)
        b = [1 + alpha * a, -2 * cos, 1 - alpha * a]
        den = [1 + alpha / a, -2 * cos, 1 - alpha / a]
    else:  # shelves; q is the shelf slope S (1 = steepest without overshoot)
        alpha = sin / 2 * np.sqrt((a + 1 / a) * (1 / q - 1) + 2)
        sq = 2 * np.sqrt(a) * alpha
        if kind == "lowshelf":
            b = [a * ((a + 1) - (a - 1) * cos + sq), 2 * a * ((a - 1) - (a + 1) * cos),
                 a * ((a + 1) - (a - 1) * cos - sq)]
            den = [(a + 1) + (a - 1) * cos + sq, -2 * ((a - 1) + (a + 1) * cos),
                   (a + 1) + (a - 1) * cos - sq]
        elif kind == "highshelf":
            b = [a * ((a + 1) + (a - 1) * cos + sq), -2 * a * ((a - 1) + (a + 1) * cos),
                 a * ((a + 1) + (a - 1) * cos - sq)]
            den = [(a + 1) - (a - 1) * cos + sq, 2 * ((a - 1) - (a + 1) * cos),
                   (a + 1) - (a - 1) * cos - sq]
        else:
            raise ValueError(f"unknown filter {kind!r}")
    return np.concatenate([np.array(b) / den[0], np.array(den) / den[0]])


@dataclass
class EqSettings:
    """The moves most Suno songs need, in dB (0 = off)."""
    bass: float = 0.0      # low shelf at 100 Hz
    mud: float = 0.0       # bell at 300 Hz (negative cleans up boxy, muddy mixes)
    harsh: float = 0.0     # bell at 3.5 kHz (negative tames harsh vocals and synths)
    air: float = 0.0       # high shelf at 10 kHz
    body: float = 0.0      # wide bell at 180 Hz: the body of guitar, piano, upright bass
    presence: float = 0.0  # wide bell at 2.5 kHz: voices and instruments step forward

    def bands(self) -> list[tuple[str, float, float, float]]:
        bands = [("lowshelf", 100.0, self.bass, 1.0), ("peak", 180.0, self.body, 0.7),
                 ("peak", 300.0, self.mud, 1.0), ("peak", 2500.0, self.presence, 0.8),
                 ("peak", 3500.0, self.harsh, 1.2), ("highshelf", 10000.0, self.air, 1.0)]
        return [b for b in bands if abs(b[2]) > 0.01]


def eq(x: np.ndarray, sr: int, settings: EqSettings) -> np.ndarray:
    bands = [b for b in settings.bands() if b[1] < 0.45 * sr]
    if not bands:
        return x
    sos = np.stack([_biquad(kind, f0, gain, q, sr) for kind, f0, gain, q in bands])
    return signal.sosfilt(sos, x, axis=0)


# -- warmth ------------------------------------------------------------------

def _pair(sr: int, lo: float, hi: float) -> np.ndarray:
    """Butterworth high-pass at lo and low-pass at hi, 2nd order each."""
    return np.vstack([signal.butter(2, lo, "highpass", fs=sr, output="sos"),
                      signal.butter(2, hi, "lowpass", fs=sr, output="sos")])


def warmth(x: np.ndarray, sr: int, amount: float) -> tuple[np.ndarray, dict]:
    """Adds the low harmonics of gentle, slightly asymmetric (tube-like)
    saturation of the low mids (100 Hz-1.2 kHz), `amount` 0-1: the body of
    guitar, piano, upright bass and voice gets denser and warmer.

    Only what the saturation adds is mixed in, from a zero-phase band, so
    nothing shifts in phase. The drive follows the band's own level (its
    loud parts reach the curve's knee), so every song gets the same colour.
    """
    stats = {"added_db": None}
    if amount <= 0:
        return x, stats
    band = signal.sosfiltfilt(_pair(sr, *WARMTH_BAND_HZ), x, axis=0)
    step = max(1, int(0.05 * sr))  # 50 ms blocks
    power = np.mean(band ** 2, axis=1)
    blocks = power[: len(power) // step * step].reshape(-1, step).mean(axis=1)
    if blocks.size == 0 or blocks.max() <= 0:
        return x, stats
    ref = np.sqrt(2 * np.percentile(blocks, 95))  # sine peak at the loud parts' level
    drive, bias = 0.25 + 0.45 * amount, 0.08 + 0.07 * amount  # 2nd harmonic ~-34 dB at 0.35
    u = band / ref
    shaped = (np.tanh(drive * u + bias) - np.tanh(bias)) / (drive * (1 - np.tanh(bias) ** 2))
    # what the curve added; keep its harmonics, drop its DC and fizz
    added = signal.sosfiltfilt(_pair(sr, 60.0, min(8000.0, 0.45 * sr)), (shaped - u) * ref, axis=0)
    total = float(np.sum(x ** 2))
    if total > 0:
        stats["added_db"] = round(10 * np.log10(max(float(np.sum(added ** 2)), 1e-30) / total), 1)
    return x + added, stats


# -- matching a reference ----------------------------------------------------

def _smooth_octave(freqs: np.ndarray, power: np.ndarray, fraction: float = 3) -> np.ndarray:
    """Averages power over 1/fraction octave around each frequency."""
    cs = np.concatenate([[0.0], np.cumsum(power)])
    lo = np.searchsorted(freqs, freqs * 2 ** (-0.5 / fraction))
    hi = np.maximum(np.searchsorted(freqs, freqs * 2 ** (0.5 / fraction), side="right"), lo + 1)
    hi = np.minimum(hi, len(power))
    return (cs[hi] - cs[lo]) / np.maximum(hi - lo, 1)


@dataclass
class Match:
    freqs: np.ndarray
    curve_db: np.ndarray  # EQ to apply
    width_db: float       # side gain to apply above the mono bass
    reference_lufs: float | None = None

    def summary(self) -> dict:
        """The curve at a few points, for the report."""
        points = (40, 80, 160, 315, 630, 1250, 2500, 5000, 10000, 16000)
        return {"eq_db": {str(f): round(float(np.interp(f, self.freqs, self.curve_db)), 1)
                          for f in points if f < self.freqs[-1]},
                "width_db": round(self.width_db, 1)}


def match_reference(x: np.ndarray, sr: int, ref: np.ndarray, ref_sr: int,
                    strength: float = 0.7) -> Match:
    """EQ curve (and stereo width) that moves x's long-term balance towards
    the reference's, scaled by strength (0-1). Loudness is left to the
    loudness stage, so the curve has zero average over 100 Hz-10 kHz."""
    freqs, p_x = average_spectrum(x, sr)
    f_ref, p_ref = average_spectrum(ref, ref_sr)
    p_ref = np.interp(freqs, f_ref, p_ref, right=0.0)
    s_x = 10 * np.log10(_smooth_octave(freqs, p_x) + 1e-20)
    s_ref = 10 * np.log10(_smooth_octave(freqs, p_ref) + 1e-20)
    curve = s_ref - s_x

    body = (freqs >= 100) & (freqs <= 10000)
    weights = 1 / np.maximum(freqs[body], 1)  # equal weight per octave
    curve -= np.sum(curve[body] * weights) / np.sum(weights)

    # Boost less up high (Suno often has little there: boosting it lifts
    # noise) and never where either song has next to nothing.
    max_boost = np.interp(freqs, [0, 12000, 18000], [MATCH_MAX_BOOST_DB, MATCH_MAX_BOOST_DB, 1.0])
    empty = (s_x < s_x.max() - 70) | (s_ref < s_ref.max() - 70)
    max_boost[empty] = 0.0
    curve = np.clip(curve, -MATCH_MAX_CUT_DB, max_boost) * strength
    curve *= np.interp(freqs, [0, 20, 30], [0, 0, 1])  # the low cut owns the subsonics
    curve[freqs >= min(20000, 0.48 * sr)] = 0.0

    width_db = 0.0
    w_x, w_ref = side_mid_ratio(x, sr), side_mid_ratio(ref, ref_sr)
    if w_x and w_ref:
        width_db = float(np.clip(10 * np.log10(w_ref / w_x), -MATCH_MAX_WIDTH_DB,
                                 MATCH_MAX_WIDTH_DB)) * strength
    return Match(freqs, curve, width_db)


def apply_curve(x: np.ndarray, sr: int, freqs: np.ndarray, curve_db: np.ndarray) -> np.ndarray:
    """Linear-phase FIR EQ (no phase shift, like Matchering's)."""
    nyq = sr / 2
    grid = np.linspace(0, nyq, 4097)
    gain = 10 ** (np.interp(grid, freqs, curve_db) / 20)
    taps = signal.firwin2(MATCH_TAPS, grid, gain, fs=sr)
    delay = (MATCH_TAPS - 1) // 2
    y = signal.oaconvolve(x, taps[:, None], mode="full", axes=0)
    return y[delay:delay + len(x)]


# -- stereo --------------------------------------------------------------------

def stereo(x: np.ndarray, sr: int, mono_bass_hz: float = 0.0, width_db: float = 0.0) -> np.ndarray:
    """Mono below mono_bass_hz (tight low end, safe on phones and vinyl) and
    the side signal above it turned up/down by width_db."""
    if x.shape[1] != 2 or (not mono_bass_hz and abs(width_db) < 0.01):
        return x
    mid = (x[:, 0] + x[:, 1]) / 2
    side = (x[:, 0] - x[:, 1]) / 2
    low = np.zeros_like(side)
    if mono_bass_hz:
        sos = signal.butter(2, mono_bass_hz, "lowpass", fs=sr, output="sos")
        low = signal.sosfiltfilt(sos, side)  # zero phase: side - low is its exact complement
    side = (side - low) * 10 ** (width_db / 20)
    return np.stack([mid + side, mid - side], axis=1)
