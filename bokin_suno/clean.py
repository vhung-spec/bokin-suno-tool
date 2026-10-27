"""Removing AI-generation artifacts: Suno "shimmer", hiss, harsh S, whines.

Works on the STFT of the song (Hann window, 75% overlap) with one gain mask
shared by both channels, so the stereo image and the phase stay as they
were. Each tool becomes a reduction in dB per time-frequency cell:

- shimmer: Suno's glassy, metallic grain in the highs is short *and* narrow.
  A cell well above both the median of its neighbours in time (so it is not
  a sustained tone) and in frequency (so it is not a broadband drum hit) is
  pulled down towards them.
- dehiss: a noise floor learned from the quietest frames is subtracted
  (spectral subtraction with a floor), in the highs only.
- deess: frames whose 5-10 kHz band jumps above the song's usual balance
  get that band turned down.
- dewhine: narrow peaks that stay put through the whole song (a whistle the
  generator left in) get a fixed cut.

The song is processed in chunks that overlap enough for the result to be the
same as processing it in one go, so memory stays small for long songs.
"""

from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
from scipy.ndimage import maximum_filter, maximum_filter1d, median_filter, uniform_filter, \
    uniform_filter1d
import scipy.fft
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal.windows import hann

SHIMMER_HZ = (3500.0, 6000.0)  # shimmer reduction fades in over this range
TIME_MEDIAN = 11               # frames, ~120 ms at 48 kHz
FREQ_MEDIAN = 15               # bins, ~350 Hz at 48 kHz
HISS_HZ = (1500.0, 3000.0)     # dehiss fades in over this range
SIBILANCE_HZ = (5000.0, 10000.0)
SIBILANCE_REF_HZ = (300.0, 4000.0)
WHINE_FROM_HZ = 2500.0
MAX_REDUCTION_DB = 30.0
EPS = 1e-12


@dataclass
class CleanSettings:
    """Strength of each tool, 0 (off) to 1 (strong)."""
    shimmer: float = 0.5
    dehiss: float = 0.0
    deess: float = 0.0
    dewhine: float = 0.5

    def active(self) -> bool:
        return max(asdict(self).values()) > 0


class _Grid:
    """STFT with a periodic Hann window and hop = n_fft / 4, in single
    precision. The signal is padded with 3 hops in front, so every sample
    lies under exactly 4 frames and frame t is centred on sample (t - 1) * hop.
    """

    def __init__(self, sr: int):
        self.sr = sr
        self.n_fft = 2048 if sr <= 50000 else 4096 if sr <= 100000 else 8192
        self.hop = self.n_fft // 4
        self.window = hann(self.n_fft, sym=False).astype(np.float32)
        self.freqs = np.fft.rfftfreq(self.n_fft, 1 / sr)
        self.bin_hz = sr / self.n_fft

    def stft(self, x: np.ndarray) -> np.ndarray:
        """(samples, channels) -> (channels, freqs, frames)."""
        h = self.hop
        frames = -(-(len(x) + 3 * h) // h)
        padded = np.zeros(((frames + 3) * h, x.shape[1]), np.float32)
        padded[3 * h:3 * h + len(x)] = x
        windows = sliding_window_view(padded, self.n_fft, axis=0)[::h]  # (frames, ch, n_fft)
        S = scipy.fft.rfft(windows * self.window, axis=-1, workers=-1)
        return S.transpose(1, 2, 0)

    def istft(self, S: np.ndarray, n: int) -> np.ndarray:
        """Inverse of stft() (weighted overlap-add); returns (n, channels)."""
        h = self.hop
        channels, _, frames = S.shape
        y = scipy.fft.irfft(S.transpose(2, 0, 1), n=self.n_fft, axis=-1, workers=-1) * self.window
        quarters = y.reshape(frames, channels, 4, h)
        out = np.zeros((frames + 3, channels, h), np.float32)
        for k in range(4):  # quarter k of frame t lands in block t + k
            out[k:k + frames] += quarters[:, :, k]
        out = out.transpose(0, 2, 1).reshape(-1, channels)
        return out[3 * h:3 * h + n] / 1.5  # sum of the squared windows at 75% overlap

    def frame_power(self, mono: np.ndarray) -> np.ndarray:
        """Power (freqs, frames) of back-to-back frames: statistics only."""
        frames = len(mono) // self.n_fft
        windows = mono[:frames * self.n_fft].astype(np.float32).reshape(frames, self.n_fft)
        S = scipy.fft.rfft(windows * self.window, axis=-1, workers=-1)
        return (S.real ** 2 + S.imag ** 2).T

    def ramp(self, lo: float, hi: float) -> np.ndarray:
        """0 below lo, 1 above hi, a raised cosine in between."""
        t = np.clip((self.freqs - lo) / (hi - lo), 0.0, 1.0)
        return (0.5 - 0.5 * np.cos(np.pi * t)).astype(np.float32)

    def band(self, lo: float, hi: float) -> np.ndarray:
        return (self.freqs >= lo) & (self.freqs < hi)


def _band_ratio_db(P: np.ndarray, grid: _Grid) -> np.ndarray:
    """Per frame: sibilance band level relative to the body of the sound."""
    sib = P[grid.band(*SIBILANCE_HZ)].sum(axis=0)
    ref = P[grid.band(*SIBILANCE_REF_HZ)].sum(axis=0)
    return 10 * np.log10(sib + EPS) - 10 * np.log10(ref + EPS)


def _find_whines(P: np.ndarray, grid: _Grid, amount: float) -> tuple[np.ndarray, list[float]]:
    """Fixed cut (dB, <= 0) per bin for narrow peaks present in most frames."""
    cut = np.zeros(len(grid.freqs), np.float32)
    if amount <= 0:
        return cut, []
    level = 10 * np.log10(P.mean(axis=1) + EPS)
    width = int(round(400 / grid.bin_hz)) | 1  # ~400 Hz neighbourhood, odd
    excess = level - median_filter(level, size=width, mode="nearest")
    frames_db = 10 * np.log10(P + EPS)
    found = []
    half = width // 2
    for k in np.flatnonzero((grid.freqs >= WHINE_FROM_HZ) & (excess > 8)):
        if not (excess[k] >= excess[k - 1] and excess[k] >= excess[min(k + 1, len(excess) - 1)]):
            continue  # only the top of each peak
        around = np.median(frames_db[max(0, k - half):k + half + 1], axis=0)
        present = np.mean(frames_db[k] - around > 6)
        steady = np.std(frames_db[k]) < 4  # a whine holds its level; notes come and go
        if not (present >= 0.8 or (present >= 0.6 and steady)):
            continue  # music, not a whine
        depth = min(24.0, (float(excess[k]) - 3) * amount)
        for j, share in ((-2, 0.5), (-1, 1.0), (0, 1.0), (1, 1.0), (2, 0.5)):
            if 0 <= k + j < len(cut):  # the Hann main lobe spreads a tone over +-2 bins
                cut[k + j] = min(cut[k + j], -depth * share)
        found.append(round(float(grid.freqs[k]), 1))
    return cut, found


def _profile(x: np.ndarray, grid: _Grid, s: CleanSettings) -> dict | None:
    """Whole-song statistics, from frames without overlap."""
    # mean of the channels' powers, like the processing below (the power of
    # a mono mix would read uncorrelated hiss 3 dB low)
    P = np.mean([grid.frame_power(x[:, c]) for c in range(x.shape[1])], axis=0)
    frame = P.sum(axis=0)
    if frame.size == 0 or frame.max() <= 0:
        return None
    floor = float(frame.max()) * 1e-6  # 60 dB below the loudest frame
    P = P[:, frame > floor]
    if P.shape[1] < 4:
        return None
    high = P[grid.freqs >= 2000].sum(axis=0)
    quietest = np.argsort(high)[:max(1, P.shape[1] // 10)]
    whine_db, whines_hz = _find_whines(P, grid, s.dewhine)
    return {
        "floor": floor,
        "noise": P[:, quietest].mean(axis=1),
        "sibilance_median": float(np.median(_band_ratio_db(P, grid))),
        "whine_db": whine_db,
        "whines_hz": whines_hz,
    }


def _reduction_db(P: np.ndarray, grid: _Grid, s: CleanSettings,
                  profile: dict) -> tuple[np.ndarray, np.ndarray | None]:
    """Reduction in dB per cell, and the de-esser's cut per frame."""
    level = 10 * np.log10(P + EPS)
    red = np.zeros(P.shape, np.float32)

    if s.shimmer > 0:
        lo = int(np.searchsorted(grid.freqs, SHIMMER_HZ[0]))
        high = level[lo:]
        around = np.maximum(median_filter(high, size=(1, TIME_MEDIAN), mode="nearest"),
                            median_filter(high, size=(FREQ_MEDIAN, 1), mode="nearest"))
        threshold = 9 - 4 * s.shimmer  # dB above the neighbourhood
        cut = np.clip((high - around - threshold) * (0.4 + 0.6 * s.shimmer),
                      0, 6 + 12 * s.shimmer)
        # A grain spreads over ~3x3 cells (window main lobe, overlap): take
        # the whole blob, then soften its edges.
        cut = uniform_filter(maximum_filter(cut, size=3, mode="nearest"), size=3, mode="nearest")
        red[lo:] -= cut * grid.ramp(*SHIMMER_HZ)[lo:, None]

    if s.dehiss > 0:
        over = 1 + 1.5 * s.dehiss  # over-subtraction factor
        floor_db = -(3 + 9 * s.dehiss)
        g2 = 1 - over * profile["noise"][:, None] / np.maximum(P, EPS)
        gain_db = 10 * np.log10(np.clip(g2, 10 ** (floor_db / 10), 1.0))
        gain_db = uniform_filter1d(gain_db, 3, axis=1, mode="nearest")  # against "musical noise"
        red += gain_db * grid.ramp(*HISS_HZ)[:, None]

    if s.deess > 0:
        over = _band_ratio_db(P, grid) - (profile["sibilance_median"] + 8 - 4 * s.deess)
        cut = np.clip(over * (0.5 + 0.5 * s.deess), 0, 3 + 7 * s.deess)
        cut[P.sum(axis=0) < profile["floor"]] = 0
        deess = uniform_filter1d(maximum_filter1d(cut, 3, mode="nearest"), 3, mode="nearest")
        weight = grid.ramp(4000, 5500) * (1 - grid.ramp(10000, 13000))
        red -= weight[:, None] * deess[None, :].astype(np.float32)
    else:
        deess = None

    red += profile["whine_db"][:, None]
    return np.maximum(red, -MAX_REDUCTION_DB), deess


def clean(x: np.ndarray, sr: int, settings: CleanSettings,
          progress: Callable[[float], None] | None = None,
          chunk_seconds: float = 10.0) -> tuple[np.ndarray, dict]:
    """Returns the cleaned audio and what was done."""
    stats = {"highs_change_db": 0.0, "deess_frames_pct": 0.0, "whines_hz": []}
    if not settings.active():
        return x.copy(), stats
    grid = _Grid(sr)
    profile = _profile(x, grid, settings)
    if profile is None:  # silence
        return x.copy(), stats
    stats["whines_hz"] = profile["whines_hz"]

    n, hop = len(x), grid.hop
    pad = 16 * hop  # > the reach of every filter above, in frames, plus a window
    chunk = max(hop, int(chunk_seconds * sr) // hop * hop)
    high = grid.freqs >= SHIMMER_HZ[0]
    energy = [0.0, 0.0]  # highs before / after
    counts = {"deess_frames": 0, "frames": 0}
    y = np.empty_like(x)
    for start in range(0, n, chunk):
        end = min(n, start + chunk)
        a, b = max(0, start - pad), min(n, end + pad)  # a stays on the hop grid
        S = grid.stft(x[a:b])
        P = (S.real ** 2 + S.imag ** 2).mean(axis=0)
        red, deess = _reduction_db(P, grid, settings, profile)
        gain = 10 ** (red / 20)
        out = grid.istft(S * gain, b - a)
        y[start:end] = out[start - a:end - a]

        # stats over the frames centred inside [start, end)
        frames = slice((start - a) // hop + 1, (end - a) // hop + 1)
        energy[0] += float(P[high, frames].sum())
        energy[1] += float((P[high, frames] * gain[high, frames] ** 2).sum())
        counts["frames"] += P[:, frames].shape[1]
        if deess is not None:
            counts["deess_frames"] += int((deess[frames] > 0.5).sum())
        if progress:
            progress(end / n)
    if energy[0] > 0:
        stats["highs_change_db"] = round(float(10 * np.log10(max(energy[1], EPS) / energy[0])), 2)
    stats["deess_frames_pct"] = round(100 * counts["deess_frames"] / max(1, counts["frames"]), 1)
    return y, stats
