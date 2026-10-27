import numpy as np
import pytest
from scipy import signal

from bokin_suno.analysis import average_spectrum, side_mid_ratio
from bokin_suno.tone import EqSettings, apply_curve, eq, lowcut, match_reference, stereo
from tests.conftest import SR, band_energy, music


def noise(seconds=6.0, seed=0):
    return np.random.default_rng(seed).standard_normal((int(seconds * SR), 2)) * 0.05


def gain_db(y, x, lo, hi):
    return 10 * np.log10(band_energy(y, SR, lo, hi) / band_energy(x, SR, lo, hi))


def test_eq_bands_hit_their_frequencies():
    x = noise()
    y = eq(x, SR, EqSettings(bass=4, mud=-3, harsh=-3, air=3))
    assert gain_db(y, x, 40, 70) == pytest.approx(4, abs=0.6)
    assert gain_db(y, x, 280, 320) == pytest.approx(-3, abs=0.5)
    assert gain_db(y, x, 3300, 3700) == pytest.approx(-3, abs=0.5)
    assert gain_db(y, x, 15000, 18000) == pytest.approx(3, abs=0.5)
    assert abs(gain_db(y, x, 1000, 1500)) < 0.6
    assert eq(x, SR, EqSettings()) is x


def test_lowcut_removes_rumble_and_dc():
    x = noise() + 0.1
    y = lowcut(x, SR, 25)
    assert abs(y.mean()) < 1e-3
    assert abs(gain_db(y, x, 200, 2000)) < 0.1


def test_mono_bass_and_width():
    x = noise()
    y = stereo(x, SR, mono_bass_hz=120)
    side_x, side_y = (x[:, 0] - x[:, 1]) / 2, (y[:, 0] - y[:, 1]) / 2
    low = lambda s: band_energy(s[:, None], SR, 20, 50)  # noqa: E731
    assert 10 * np.log10(low(side_y) / low(side_x)) < -20
    assert abs(gain_db(side_y[:, None], side_x[:, None], 1000, 5000)) < 0.1
    np.testing.assert_allclose(y.mean(axis=1), x.mean(axis=1), atol=1e-12)  # mid untouched
    wide = stereo(x, SR, width_db=3)
    assert 10 * np.log10(side_mid_ratio(wide, SR) / side_mid_ratio(x, SR)) == pytest.approx(3, abs=0.1)


def test_match_moves_the_balance_towards_the_reference():
    ref = noise(seed=1)
    tilt = signal.butter(1, 2000, "lowpass", fs=SR, output="sos")
    x = signal.sosfilt(tilt, noise(seed=2), axis=0)  # dull compared with the reference
    m = match_reference(x, SR, ref, SR, strength=1.0)
    y = apply_curve(x, SR, m.freqs, m.curve_db)

    def balance(z):  # highs relative to lows, dB
        return 10 * np.log10(band_energy(z, SR, 5000, 9000) / band_energy(z, SR, 300, 600))
    assert abs(balance(y) - balance(ref)) < 0.4 * abs(balance(x) - balance(ref))
    assert set(m.summary()) == {"eq_db", "width_db"}


def test_match_limits_boost_where_the_song_is_empty():
    ref = noise(seed=1)
    x = signal.sosfilt(signal.butter(8, 15000, "lowpass", fs=SR, output="sos"), noise(seed=2), axis=0)
    m = match_reference(x, SR, ref, SR, strength=1.0)
    assert m.curve_db[m.freqs > 18000].max() <= 1.0 + 1e-9


def test_apply_curve_keeps_timing():
    x = music(2.0)
    freqs = np.linspace(0, SR / 2, 100)
    y = apply_curve(x, SR, freqs, np.zeros_like(freqs))
    np.testing.assert_allclose(y, x, atol=1e-3)


def test_average_spectrum_shape():
    f, p = average_spectrum(noise(), SR)
    assert f[0] == 0 and f[-1] == SR / 2 and len(f) == len(p)
