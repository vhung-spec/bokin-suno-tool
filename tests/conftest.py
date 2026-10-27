import numpy as np
import pytest
from scipy import signal

SR = 48000


def music(seconds: float = 8.0, sr: int = SR, seed: int = 0) -> np.ndarray:
    """A small stereo "song": chords with harmonics, bass, kicks, hi-hats."""
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n) / sr
    x = np.zeros((n, 2))
    for i, start in enumerate(np.arange(0, seconds, 2.0)):
        a, b = int(start * sr), min(n, int((start + 2.0) * sr))
        tt = t[a:b] - start
        env = np.minimum(1, tt / 0.02) * np.exp(-tt * 0.6)
        root = (220, 196, 174.6, 246.9)[i % 4]
        for ratio in (1, 1.25, 1.5):
            for h in range(1, 10):
                ph = rng.uniform(0, 2 * np.pi)
                amp = 0.05 / h ** 1.2
                x[a:b, 0] += amp * env * np.sin(2 * np.pi * root * ratio * h * tt + ph)
                x[a:b, 1] += amp * env * np.sin(2 * np.pi * root * ratio * h * tt + ph + 0.3)
    x += (0.15 * np.sin(2 * np.pi * 55 * t))[:, None]
    hp = signal.butter(4, 7000, "highpass", fs=sr, output="sos")
    for k in np.arange(0, seconds - 0.3, 0.5):
        a = int(k * sr)
        tt = np.arange(int(0.25 * sr)) / sr
        x[a:a + len(tt)] += (0.6 * np.sin(2 * np.pi * (50 + 80 * np.exp(-tt * 30)) * tt)
                             * np.exp(-tt * 12))[:, None]
        a2 = int((k + 0.25) * sr)
        m = int(0.05 * sr)
        hat = rng.standard_normal((m, 2)) * np.exp(-np.arange(m) / sr * 80)[:, None] * 0.08
        x[a2:a2 + m] += signal.sosfilt(hp, hat, axis=0)
    return x


def whine(seconds: float = 8.0, sr: int = SR, hz: float = 7350.0, amp: float = 0.004) -> np.ndarray:
    t = np.arange(int(seconds * sr)) / sr
    return np.repeat((amp * np.sin(2 * np.pi * hz * t))[:, None], 2, axis=1)


def band_energy(x: np.ndarray, sr: int, lo: float, hi: float) -> float:
    sos = signal.butter(4, [lo, hi], "bandpass", fs=sr, output="sos")
    return float(np.sum(signal.sosfilt(sos, x, axis=0) ** 2))


@pytest.fixture(scope="session")
def song() -> np.ndarray:
    return music()
