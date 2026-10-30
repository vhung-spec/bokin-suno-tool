import numpy as np
import pytest

from bokin_suno.clean import CleanSettings, _Grid, clean
from tests.conftest import SR, band_energy, music, whine


def test_stft_round_trip_is_exact():
    x = music(3.0)
    grid = _Grid(SR)
    np.testing.assert_allclose(grid.istft(grid.stft(x), len(x)), x, atol=1e-5)


def test_off_is_a_copy(song):
    y, stats = clean(song, SR, CleanSettings(0, 0, 0, 0))
    np.testing.assert_array_equal(y, song)
    assert stats["whines_hz"] == []


def test_chunks_give_the_same_result_as_one_go(song):
    settings = CleanSettings(shimmer=1, dehiss=0.5, deess=0.5, dewhine=1)
    whole, _ = clean(song, SR, settings, chunk_seconds=60)
    chunked, _ = clean(song, SR, settings, chunk_seconds=1.3)
    np.testing.assert_allclose(chunked, whole, atol=2e-5)


def test_removes_a_steady_whine_and_spares_the_music(song):
    noisy = song + whine()
    y, stats = clean(noisy, SR, CleanSettings(shimmer=0, dewhine=0.5))
    assert stats["whines_hz"] and abs(stats["whines_hz"][0] - 7350) < 30
    before = band_energy(noisy - song, SR, 7200, 7500)
    after = band_energy(y - song, SR, 7200, 7500)
    assert 10 * np.log10(after / before) < -8
    _, clean_stats = clean(song, SR, CleanSettings(shimmer=0, dewhine=1))
    assert clean_stats["whines_hz"] == []  # sustained chord notes are not whines


def test_a_repeated_high_note_is_not_a_whine(song):
    # a piano ostinato: A6 struck every half second through the whole song,
    # its overtones (3.5, 5.3, 7 kHz) are there in every frame
    t = np.arange(int(0.5 * SR)) / SR
    note = sum(0.02 / k * np.exp(-t * (3 + k)) * np.sin(2 * np.pi * 1760 * k * np.sqrt(1 + 0.0002 * k * k) * t)
               for k in range(1, 5))
    ostinato = np.repeat(np.tile(note, len(song) // len(note) + 1)[:len(song), None], 2, axis=1)
    y, stats = clean(song + ostinato, SR, CleanSettings(shimmer=0, dewhine=1))
    assert stats["whines_hz"] == []
    np.testing.assert_allclose(y, song + ostinato, atol=1e-6)
    _, stats = clean(song + ostinato + whine(), SR, CleanSettings(shimmer=0, dewhine=0.5))
    assert len(stats["whines_hz"]) == 1 and abs(stats["whines_hz"][0] - 7350) < 30  # a lone whine still goes


def test_shimmer_pulls_down_short_narrow_grains(song):
    rng = np.random.default_rng(3)
    grains = np.zeros_like(song)
    for _ in range(120):
        f, m = rng.uniform(5000, 14000), int(rng.uniform(0.008, 0.025) * SR)
        a = rng.integers(0, len(song) - m)
        burst = 0.02 * np.hanning(m) * np.sin(2 * np.pi * f * np.arange(m) / SR)
        grains[a:a + m, rng.integers(0, 2)] += burst
    y, _ = clean(song + grains, SR, CleanSettings(shimmer=1, dewhine=0))
    left = band_energy(y - song, SR, 4500, 15000) / band_energy(grains, SR, 4500, 15000)
    assert 10 * np.log10(left) < -2.5
    untouched, _ = clean(song, SR, CleanSettings(shimmer=0.5, dewhine=0))
    change = band_energy(untouched - song, SR, 4000, 20000) / band_energy(song, SR, 4000, 20000)
    assert 10 * np.log10(change) < -35  # the clean song barely changes


def test_shimmer_keeps_noise_like_cymbals():
    noise = np.random.default_rng(1).standard_normal((SR * 6, 2)) * 0.05
    y, _ = clean(noise, SR, CleanSettings(shimmer=0.5, dewhine=0))
    assert abs(10 * np.log10(band_energy(y, SR, 4000, 20000) / band_energy(noise, SR, 4000, 20000))) < 0.2


def test_dehiss_lowers_the_noise_floor(song):
    hiss = np.random.default_rng(2).standard_normal(song.shape) * 0.002
    y, _ = clean(song + hiss, SR, CleanSettings(shimmer=0, dehiss=0.6, dewhine=0))
    left = band_energy(y - song, SR, 3000, 20000) / band_energy(hiss, SR, 3000, 20000)
    assert 10 * np.log10(left) < -2


def test_deess_turns_down_sibilant_bursts(song):
    rng = np.random.default_rng(4)
    from scipy import signal
    s = np.zeros_like(song)
    for k in (1.0, 3.0, 5.0):  # three loud "s" sounds
        a, m = int(k * SR), int(0.15 * SR)
        s[a:a + m] = rng.standard_normal((m, 2)) * 0.15
    s = signal.sosfilt(signal.butter(4, [5000, 9000], "bandpass", fs=SR, output="sos"), s, axis=0)
    y, stats = clean(song + s, SR, CleanSettings(shimmer=0, deess=0.7, dewhine=0))
    assert stats["deess_frames_pct"] > 0
    assert band_energy(y, SR, 5000, 9000) < 0.7 * band_energy(song + s, SR, 5000, 9000)


@pytest.mark.parametrize("sr", [44100, 96000])
def test_other_sample_rates(sr):
    x = music(3.0, sr=sr)
    y, _ = clean(x, sr, CleanSettings())
    assert y.shape == x.shape and np.isfinite(y).all()


def test_mono_and_silence():
    mono = music(3.0)[:, :1]
    y, _ = clean(mono, SR, CleanSettings())
    assert y.shape == mono.shape
    silent = np.zeros((SR * 2, 2))
    y, _ = clean(silent, SR, CleanSettings(1, 1, 1, 1))
    np.testing.assert_array_equal(y, silent)
