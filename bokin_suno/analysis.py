"""Measurements: loudness (ITU-R BS.1770-4 / EBU R128), true peak, spectrum.

Loudness is computed here rather than with pyloudnorm because the loudness
stage measures the song several times: the block energies come from one
cumulative sum, so a measurement takes a fraction of a second.
"""

import numpy as np
from scipy import signal

OVERSAMPLE = 4  # true peak per BS.1770: 4x oversampling
_TP_TAPS = 24   # per phase of the interpolation filter
ABSOLUTE_GATE = -70.0


def db(value: float) -> float:
    return float(20 * np.log10(value)) if value > 0 else float("-inf")


def _k_weighting(sr: int) -> np.ndarray:
    """The BS.1770 pre-filter (head shelf + RLB high-pass) for any sample
    rate, as derived in libebur128; at 48 kHz it gives the spec's numbers."""
    f0, gain, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    k = np.tan(np.pi * f0 / sr)
    vh = 10 ** (gain / 20)
    vb = vh ** 0.4996667741545416
    a0 = 1 + k / q + k * k
    shelf = [(vh + vb * k / q + k * k) / a0, 2 * (k * k - vh) / a0, (vh - vb * k / q + k * k) / a0,
             1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]
    f0, q = 38.13547087602444, 0.5003270373238773
    k = np.tan(np.pi * f0 / sr)
    a0 = 1 + k / q + k * k
    highpass = [1.0, -2.0, 1.0, 1.0, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]
    return np.array([shelf, highpass])


def k_weighted_energy(x: np.ndarray, sr: int) -> np.ndarray:
    """Per sample: K-weighted square, summed over channels (L, R weight 1)."""
    weighted = signal.sosfilt(_k_weighting(sr), x, axis=0)
    energy = weighted[:, 0] ** 2
    for c in range(1, x.shape[1]):
        energy += weighted[:, c] ** 2
    return energy


def _block_power(energy: np.ndarray, sr: int, block_s: float, step_s: float) -> np.ndarray:
    """Mean of energy per gating block."""
    cs = np.concatenate([[0.0], np.cumsum(energy)])
    size = int(round(block_s * sr))
    if len(energy) < size:
        return np.array([cs[-1] / size])  # one block, the rest is silence
    starts = (np.arange(int((len(energy) - size) / (step_s * sr)) + 1) * step_s * sr).astype(int)
    return (cs[starts + size] - cs[starts]) / size


def _loudness(power: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return -0.691 + 10 * np.log10(power)


def lufs(x: np.ndarray, sr: int) -> float:
    """Integrated loudness in LUFS (-inf for silence)."""
    return lufs_from_energy(k_weighted_energy(x, sr), sr)


def lufs_from_energy(energy: np.ndarray, sr: int) -> float:
    power = _block_power(energy, sr, 0.4, 0.1)
    power = power[_loudness(power) > ABSOLUTE_GATE]
    if power.size == 0:
        return float("-inf")
    relative = _loudness(power.mean()) - 10
    gated = power[_loudness(power) > relative]
    return float(_loudness(gated.mean()))


def loudness_range(x: np.ndarray, sr: int, energy: np.ndarray | None = None) -> float | None:
    """Loudness range (EBU Tech 3342) in LU, None when too short or quiet.
    energy: k_weighted_energy(x), when already known."""
    if len(x) < 3 * sr:
        return None
    if energy is None:
        energy = k_weighted_energy(x, sr)
    short_term = _loudness(_block_power(energy, sr, 3.0, 0.1))
    short_term = short_term[short_term > ABSOLUTE_GATE]
    if short_term.size == 0:
        return None
    relative = _loudness(np.mean(10 ** ((short_term + 0.691) / 10))) - 20
    short_term = short_term[short_term > relative]
    low, high = np.percentile(short_term, [10, 95])
    return float(high - low)


def _interpolation_phases() -> np.ndarray:
    """Polyphase FIR taps that give the signal at n + 1/4, 1/2, 3/4."""
    length = OVERSAMPLE * _TP_TAPS + 1
    proto = signal.firwin(length, 1 / OVERSAMPLE, window=("kaiser", 8.0)) * OVERSAMPLE
    return np.stack([proto[p::OVERSAMPLE][:_TP_TAPS] for p in range(1, OVERSAMPLE)])


_PHASES = _interpolation_phases()


def true_peak_envelope(x: np.ndarray) -> np.ndarray:
    """Per sample n, the highest |value| of the 4x oversampled signal in
    [n, n+1) over all channels: where the waveform peaks between samples,
    which a DAC (or an MP3 decoder) will reproduce."""
    delay = _TP_TAPS // 2  # phase p at output n + delay is the signal at n + p/4
    n = len(x)
    out = np.abs(x[:, 0])
    for c in range(x.shape[1]):
        ch = np.ascontiguousarray(x[:, c])
        if c:
            np.maximum(out, np.abs(ch), out=out)
        for taps in _PHASES:
            phase = np.convolve(ch, taps)[delay:delay + n]
            np.maximum(out, np.abs(phase, out=phase), out=out)
    return out


def true_peak_db(x: np.ndarray) -> float:
    return db(float(true_peak_envelope(x).max()))


def measure(x: np.ndarray, sr: int, true_peak: float | None = None) -> dict:
    """Report numbers for x. true_peak: its true peak in dBTP, when known."""
    energy = k_weighted_energy(x, sr)
    lra = loudness_range(x, sr, energy)
    peak = float(np.abs(x).max())
    return {
        "lufs": round(lufs_from_energy(energy, sr), 2),
        "true_peak_db": round(true_peak_db(x) if true_peak is None else true_peak, 2),
        "sample_peak_db": round(db(peak), 2),
        "lra": None if lra is None else round(lra, 1),
        # samples at full scale: the song was clipped somewhere upstream
        "clipped_samples": int(np.count_nonzero(np.abs(x) >= 0.9999)),
        "seconds": round(len(x) / sr, 2),
        "sample_rate": sr,
        "channels": x.shape[1],
    }


def average_spectrum(x: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """Long-term power spectrum of the mid (mono) signal, ~3 Hz resolution."""
    mid = x.mean(axis=1)
    nperseg = 1 << int(np.ceil(np.log2(sr / 3)))
    nperseg = min(nperseg, 1 << int(np.log2(max(len(mid), 256))))
    return signal.welch(mid, sr, nperseg=nperseg)


def side_mid_ratio(x: np.ndarray, sr: int, low_hz: float = 200.0) -> float | None:
    """Side-to-mid power above low_hz: how wide the stereo image is."""
    if x.shape[1] != 2:
        return None
    sos = signal.butter(2, low_hz, "highpass", fs=sr, output="sos")
    mid = signal.sosfilt(sos, (x[:, 0] + x[:, 1]) / 2)
    side = signal.sosfilt(sos, (x[:, 0] - x[:, 1]) / 2)
    pm = float(np.mean(mid ** 2))
    return float(np.mean(side ** 2)) / pm if pm > 0 else None
