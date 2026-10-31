import json

import numpy as np
import pytest
import soundfile as sf
from scipy import signal

from bokin_suno import audio_io
from bokin_suno.analysis import lufs, true_peak_db
from bokin_suno.master import PRESETS, Settings, master_file, preset, process
from tests.conftest import SR, band_energy, music, whine


@pytest.fixture
def wav(tmp_path, song):
    path = tmp_path / "Bài hát.wav"
    sf.write(path, song + whine(), SR, subtype="PCM_24")
    return path


def test_everything_off_is_transparent(song):
    settings = preset("clean_only", lowcut_hz=0, clean={"shimmer": 0, "dewhine": 0},
                      ceiling_db=0)
    y, removed, report = process(song, SR, settings)
    np.testing.assert_allclose(y, song, atol=1e-12)
    assert removed is None and report["stages"]["loudness"]["max_gr_db"] == 0


@pytest.mark.parametrize("name,target", [("streaming", -14.0), ("loud", -10.0), ("gentle", -16.0),
                                         ("bossa", -14.0), ("jazz", -14.0), ("dark_piano", -16.0),
                                         ("classical_christmas", -16.0)])
def test_presets_hit_loudness_and_ceiling(song, name, target):
    y, removed, report = process(song, SR, preset(name))
    assert lufs(y, SR) == pytest.approx(target, abs=0.15)
    assert true_peak_db(y) <= preset(name).ceiling_db + 1e-6
    assert report["output"]["lufs"] == pytest.approx(target, abs=0.15)
    assert removed is not None and removed.shape == y.shape


def test_bossa_is_closest_and_jazz_keeps_more_dynamics():
    # a soft verse, then a full chorus: bossa brings the verse closest, jazz
    # less so, both closer than the streaming preset
    x = music(12.0)
    x[: 6 * SR] *= 0.25
    gap = {}
    for name in ("streaming", "bossa", "jazz"):
        y, _, report = process(x, SR, preset(name))
        gap[name] = lufs(y[6 * SR:], SR) - lufs(y[: 6 * SR], SR)
        assert report["output"]["lufs"] == pytest.approx(-14, abs=0.15)
        if name != "streaming":
            assert {"warmth", "density"} <= set(report["stages"])
    assert gap["bossa"] < gap["jazz"] - 0.5
    assert gap["jazz"] < gap["streaming"]


def _piano(seconds: float = 10.0) -> np.ndarray:
    """Low octaves and a high melody with long decays and hammer knocks (a
    piano's peaks stand high over its loudness), a pause from 7 to 8.5 s (only
    hiss), and Suno's hiss all through."""
    rng = np.random.default_rng(4)
    n = int(seconds * SR)
    x = np.zeros((n, 2))
    for i, start in enumerate(np.arange(0, 7, 1.0)):
        a = int(start * SR)
        tt = np.arange(min(n, int(8.5 * SR)) - a) / SR
        for f0, amp in ((55.0 * (1, 1.33, 1.2, 1.5)[i % 4], 0.3), (440.0 * (1, 1.12, 0.89)[i % 3], 0.15)):
            for k in range(1, 12):
                fk = k * f0 * np.sqrt(1 + 0.0003 * k * k)
                if fk < SR / 2.2:
                    x[a:a + len(tt)] += (amp / k ** 1.3 * np.exp(-tt * (1.5 + fk / 1500))
                                         * np.sin(2 * np.pi * fk * tt))[:, None]
        knock = rng.standard_normal(int(0.006 * SR)) * np.exp(-np.arange(int(0.006 * SR)) / SR * 700)
        x[a:a + len(knock)] += 0.25 * knock[:, None]
    x += signal.sosfilt(signal.butter(2, 2500, "highpass", fs=SR, output="sos"),
                        rng.standard_normal((n, 2)), axis=0) * 3e-4
    return x


def test_dark_piano_is_deeper_softer_and_cleaner_in_the_quiet():
    x = _piano()
    runs = {name: process(x, SR, preset(name)) for name in ("streaming", "dark_piano")}
    out = {name: run[0] for name, run in runs.items()}

    def level(y, lo, hi, a=0.0, b=None):  # dB relative to the song's loudness
        part = y[int(a * SR):None if b is None else int(b * SR)]
        return 10 * np.log10(band_energy(part, SR, lo, hi) / len(part)) - lufs(y, SR)

    change = {band: level(out["dark_piano"], *band) - level(out["streaming"], *band)
              for band in ((50, 120), (2500, 5000))}
    assert change[(50, 120)] > 0.8      # weight in the low octaves
    assert change[(2500, 5000)] < -1.0  # Suno's hammer clang softened
    pause = {name: level(y, 4000, 16000, 7.6, 8.4) for name, y in out.items()}
    assert pause["dark_piano"] < pause["streaming"] - 2  # less hiss where the piano stops
    limiting = {name: run[2]["stages"]["loudness"]["max_gr_db"] for name, run in runs.items()}
    assert limiting["dark_piano"] < limiting["streaming"] - 1  # the hammers keep their attack


SIBILANTS, BELLS = (1.0, 3.0, 5.0, 7.0), (2.0, 4.5, 6.5)


def _carol(seconds: float = 10.0) -> np.ndarray:
    """A string chord, soft until 4 s and loud until 8.5 s, then a pause (only
    hiss); a choir's "s" at SIBILANTS, glockenspiel hits at BELLS."""
    rng = np.random.default_rng(6)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    chord = sum(0.03 / k * np.sin(2 * np.pi * f * k * t + rng.uniform(0, 6))
                for f in (196.0, 246.9, 293.7) for k in range(1, 25) if f * k < 7000)
    level = np.interp(t, [0, 3.95, 4.05, 8.45, 8.55, seconds], [0.25, 0.25, 1, 1, 0, 0])
    x = np.repeat((chord * level)[:, None], 2, axis=1)
    m = int(0.12 * SR)
    s = signal.sosfilt(signal.butter(4, [4500, 11000], "bandpass", fs=SR, output="sos"), rng.standard_normal(m))
    for at in SIBILANTS:
        x[int(at * SR):int(at * SR) + m] += (0.06 * np.interp(at, t, level) * s * np.hanning(m))[:, None]
    tt = np.arange(int(1.5 * SR)) / SR
    bell = sum(a * np.exp(-tt * d) * np.sin(2 * np.pi * 1568 * r * tt)
               for r, a, d in ((1, 0.06, 1.2), (2.76, 0.03, 2.5), (5.4, 0.015, 5)))
    for at in BELLS:
        x[int(at * SR):int(at * SR) + len(bell)] += bell[:, None]
    x += signal.sosfilt(signal.butter(2, 2500, "highpass", fs=SR, output="sos"),
                        rng.standard_normal((n, 2)), axis=0) * 2e-4
    return x


def test_classical_christmas_keeps_dynamics_and_bells_and_softens_the_choirs_s():
    x = _carol()
    out = {name: process(x, SR, preset(name))[0] for name in ("streaming", "jazz", "classical_christmas")}

    def level(y, lo, hi, a, b):
        part = y[int(a * SR):int(b * SR)]
        return 10 * np.log10(band_energy(part, SR, lo, hi) / len(part) + 1e-30)

    def jump(y, times, lo, hi, length):  # how far a band rises at the events over just before
        return np.mean([level(y, lo, hi, at, at + length) - level(y, lo, hi, at - 0.3, at - 0.05) for at in times])

    def change(f, other="streaming"):
        return f(out["classical_christmas"]) - f(out[other])

    assert change(lambda y: jump(y, SIBILANTS, 5000, 10000, 0.12)) < -0.5  # the choir's "s" softer
    assert change(lambda y: jump(y, BELLS, 4000, 9000, 0.15)) > -0.3       # bells as bright as before
    assert change(lambda y: np.mean([level(y, 8200, 8750, at, at + 0.3) for at in BELLS])
                  - level(y, 150, 1200, 4, 8)) > 0                          # their top partial too
    assert change(lambda y: level(y, 4000, 16000, 8.7, 9.9) - lufs(y, SR)) < -2  # less hiss in the pause

    def soft_to_loud(y):  # in the strings' band only, which neither EQ nor bells change
        return level(y, 150, 1200, 5, 8) - level(y, 150, 1200, 1, 3.8)

    assert change(soft_to_loud) > -0.5           # pianissimo stays as far below the tutti as plainly mastered
    assert change(soft_to_loud, "jazz") > 0.7    # and further than a preset that lifts the quiet parts


def test_reference_loudness(song):
    quiet_ref = music(6.0, seed=5) * 0.2
    y, _, report = process(song, SR, preset("streaming", match_loudness=True), (quiet_ref, SR))
    assert lufs(y, SR) == pytest.approx(lufs(quiet_ref, SR), abs=0.2)
    assert "eq_db" in report["stages"]["match"]


def test_master_file_writes_results(tmp_path, wav):
    result = master_file(wav, tmp_path / "out", preset("streaming"))
    assert result.output.name == "Bài hát_master.wav"
    from bokin_suno.master import output_name
    assert output_name(wav, preset("bossa"), "Bossa nova") == "Bài hát_master_Bossa nova.wav"
    assert output_name(wav, preset("bossa"), 'a/b:"c  d.') == "Bài hát_master_a b c d.wav"
    assert result.removed.name == "Bài hát_removed.wav"
    report = json.loads((tmp_path / "out" / "Bài hát_report.json").read_text(encoding="utf-8"))
    assert report["output_file"] == result.output.name
    assert report["stages"]["clean"]["whines_hz"]
    x, sr = audio_io.load(result.output)
    assert sr == SR and sf.info(result.output).subtype == "PCM_24"
    assert lufs(x, sr) == pytest.approx(-14, abs=0.15)
    assert not list((tmp_path / "out").glob(".*partial*"))


@pytest.mark.parametrize("fmt,bits,sr_out,subtype", [
    ("wav", 16, 44100, "PCM_16"), ("flac", 24, None, "PCM_24"), ("mp3", 24, None, "MPEG_LAYER_III")])
def test_output_formats(tmp_path, wav, fmt, bits, sr_out, subtype):
    settings = preset("streaming", format=fmt, bits=bits, sample_rate=sr_out, write_removed=False)
    result = master_file(wav, tmp_path, settings)
    info = sf.info(result.output)
    assert info.subtype == subtype and info.samplerate == (sr_out or SR)
    assert result.removed is None
    if fmt == "mp3":  # the report measures the decoded MP3
        assert result.report["output"]["lufs"] == pytest.approx(-14, abs=0.5)


def test_settings_round_trip_and_validation():
    s = preset("loud", clean={"deess": 0.4})
    assert s.clean.deess == 0.4 and s.clean.shimmer == 0.5  # partial override keeps the rest
    assert Settings.from_dict(json.loads(json.dumps(s.to_dict()))) == s
    assert Settings.from_dict({"target_lufs": "-12", "bits": "16"}).bits == 16
    with pytest.raises(ValueError):
        Settings.from_dict({"loudness": -14})
    with pytest.raises(ValueError):
        Settings.from_dict({"clean": {"shimmer": 2}}).check()
    with pytest.raises(ValueError):
        Settings(format="flac", bits=32).check()
    with pytest.raises(ValueError):
        Settings(format="mp3").check(sr=96000)
    with pytest.raises(ValueError):
        preset("nope")
    assert set(PRESETS) == {"streaming", "loud", "gentle", "clean_only", "bossa", "jazz", "dark_piano",
                            "classical_christmas"}


def test_kiểu_master():
    from bokin_suno.master import Settings, preset, style_of
    assert style_of(preset("bossa"), "bossa") == {"preset": "bossa", "custom": False, "label": "Bossa nova"}
    assert style_of(preset("bossa")) == style_of(preset("bossa"), "bossa"), "told by the settings alone"
    moved = Settings.from_dict({**preset("dark_piano").to_dict(), "warmth": 0.35})
    assert style_of(moved, "dark_piano")["label"] == "Dark piano (đã chỉnh)"
    assert style_of(moved) == {"preset": None, "custom": True, "label": "Tuỳ chỉnh"}
    as_mp3 = Settings.from_dict({**preset("classical_christmas").to_dict(), "format": "mp3", "bits": 16,
                                 "sample_rate": 44100})
    assert style_of(as_mp3, "classical_christmas")["label"] == "Giáng sinh cổ điển", "the format is not the sound"
    assert style_of(preset("jazz"), "nope")["label"] == "Jazz"
