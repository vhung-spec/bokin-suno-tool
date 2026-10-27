import numpy as np
import pytest
from scipy import signal

from bokin_suno import analysis
from tests.conftest import SR, music


def sine(hz, amp, seconds=5.0, sr=SR, phase=0.0, channels=2):
    t = np.arange(int(seconds * sr)) / sr
    return np.repeat((amp * np.sin(2 * np.pi * hz * t + phase))[:, None], channels, axis=1)


def test_k_weighting_matches_the_spec_at_48k():
    shelf, highpass = analysis._k_weighting(48000)
    np.testing.assert_allclose(shelf, [1.53512485958697, -2.69169618940638, 1.19839281085285,
                                       1, -1.69065929318241, 0.73248077421585], atol=1e-9)
    np.testing.assert_allclose(highpass[3:], [1, -1.99004745483398, 0.99007225036621], atol=1e-9)


@pytest.mark.parametrize("sr", [44100, 48000])
def test_sine_loudness(sr):
    # BS.1770: a 1 kHz sine at 0 dBFS in both channels reads about 0 LUFS
    assert analysis.lufs(sine(997, 0.1, sr=sr), sr) == pytest.approx(-20.0, abs=0.15)
    assert analysis.lufs(sine(997, 0.1, sr=sr, channels=1), sr) == pytest.approx(-23.0, abs=0.15)


def test_silence_and_short_input():
    assert analysis.lufs(np.zeros((SR, 2)), SR) == float("-inf")
    assert np.isfinite(analysis.lufs(sine(997, 0.5, seconds=0.1), SR))
    assert analysis.loudness_range(sine(997, 0.5, seconds=1.0), SR) is None


def test_agrees_with_pyloudnorm():
    pyloudnorm = pytest.importorskip("pyloudnorm")
    x = music(12.0)
    ours = analysis.lufs(x, SR)
    theirs = pyloudnorm.Meter(SR).integrated_loudness(x)  # RBJ approximation of the filters
    assert ours == pytest.approx(theirs, abs=0.1)


def test_true_peak_finds_peaks_between_samples():
    # fs/4 with a 45 degree phase: every sample misses the crest by 3 dB
    x = sine(SR / 4, 0.5, seconds=1.0, phase=np.pi / 4)
    assert analysis.db(np.abs(x).max()) == pytest.approx(-9.03, abs=0.05)
    inner = analysis.true_peak_envelope(x)[1000:-1000].max()
    assert analysis.db(inner) == pytest.approx(-6.02, abs=0.05)


def test_true_peak_matches_fine_oversampling():
    x = music(3.0) * 0.9
    fine = np.abs(signal.resample_poly(x, 16, 1, axis=0)).max()
    assert analysis.true_peak_db(x) == pytest.approx(analysis.db(fine), abs=0.1)


def test_measure_report():
    m = analysis.measure(music(6.0), SR)
    assert set(m) >= {"lufs", "true_peak_db", "sample_peak_db", "lra", "clipped_samples"}
    assert m["true_peak_db"] >= m["sample_peak_db"]
    assert m["channels"] == 2 and m["seconds"] == 6.0
