import numpy as np

from bokin_suno.analysis import db, lufs, true_peak_db, true_peak_envelope
from bokin_suno.dynamics import density, glue, limit, limiter_gain
from tests.conftest import SR, music


def test_limiter_gain_never_lets_a_peak_through():
    rng = np.random.default_rng(1)
    env = np.abs(rng.standard_normal(SR * 3)) * np.repeat(rng.uniform(0.2, 3, 30), SR // 10)
    gain = limiter_gain(env, SR, -1.0)
    assert (env * gain).max() <= 10 ** (-1 / 20) + 1e-9
    assert gain.max() <= 1.0


def test_limit_keeps_true_peak_under_the_ceiling():
    x = music(6.0)
    y, stats = limit(x, SR, ceiling_db=-1.0, gain=10 ** (8 / 20))
    assert true_peak_db(y) <= -1.0 + 1e-6
    assert stats["max_gr_db"] > 3
    assert lufs(y, SR) > lufs(x, SR) + 4  # louder, as asked


def test_limit_leaves_quiet_audio_alone():
    x = music(4.0) * 0.1
    y, stats = limit(x, SR, ceiling_db=-1.0)
    np.testing.assert_array_equal(y, x)
    assert stats["max_gr_db"] == 0


def test_glue_compresses_loud_parts_only():
    x = music(8.0)
    x[: len(x) // 2] *= 0.3  # a quiet verse, then a loud chorus
    y, stats = glue(x, SR, amount=0.6)
    assert 0.5 < stats["max_gr_db"] < 8
    quiet_change = db(np.std(y[: len(x) // 2])) - db(np.std(x[: len(x) // 2]))
    loud_change = db(np.std(y[len(x) // 2:])) - db(np.std(x[len(x) // 2:]))
    assert abs(quiet_change) < 0.2 and loud_change < -0.5


def test_density_lifts_quiet_parts_and_keeps_peaks():
    x = music(8.0)
    x[: len(x) // 2] *= 0.2
    y, stats = density(x, SR, amount=0.5)
    gap_x = db(np.std(x[len(x) // 2:])) - db(np.std(x[: len(x) // 2]))
    gap_y = db(np.std(y[len(x) // 2:])) - db(np.std(y[: len(x) // 2]))
    assert gap_y < gap_x - 1.5 and stats["detail_lift_db"] > 1.5
    # never quieter than the song itself (the copy only adds)
    assert np.all(np.abs(y) >= np.abs(x) - 1e-12)
    same, _ = density(x, SR, 0)
    assert same is x


def test_glue_off_is_a_no_op():
    x = music(2.0)
    y, _ = glue(x, SR, amount=0)
    assert y is x


def test_envelope_is_per_sample():
    x = music(2.0)
    assert true_peak_envelope(x).shape == (len(x),)
