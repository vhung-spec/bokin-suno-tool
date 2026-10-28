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
                                         ("bossa", -14.0), ("jazz", -14.0), ("dark_piano", -16.0)])
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


def test_reference_loudness(song):
    quiet_ref = music(6.0, seed=5) * 0.2
    y, _, report = process(song, SR, preset("streaming", match_loudness=True), (quiet_ref, SR))
    assert lufs(y, SR) == pytest.approx(lufs(quiet_ref, SR), abs=0.2)
    assert "eq_db" in report["stages"]["match"]


def test_master_file_writes_results(tmp_path, wav):
    result = master_file(wav, tmp_path / "out", preset("streaming"))
    assert result.output.name == "Bài hát_master.wav"
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
    assert set(PRESETS) == {"streaming", "loud", "gentle", "clean_only", "bossa", "jazz", "dark_piano"}
