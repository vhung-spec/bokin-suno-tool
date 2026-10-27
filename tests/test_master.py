import json

import numpy as np
import pytest
import soundfile as sf

from bokin_suno import audio_io
from bokin_suno.analysis import lufs, true_peak_db
from bokin_suno.master import PRESETS, Settings, master_file, preset, process
from tests.conftest import SR, music, whine


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


@pytest.mark.parametrize("name,target", [("streaming", -14.0), ("loud", -10.0), ("gentle", -16.0)])
def test_presets_hit_loudness_and_ceiling(song, name, target):
    y, removed, report = process(song, SR, preset(name))
    assert lufs(y, SR) == pytest.approx(target, abs=0.15)
    assert true_peak_db(y) <= preset(name).ceiling_db + 1e-6
    assert report["output"]["lufs"] == pytest.approx(target, abs=0.15)
    assert removed is not None and removed.shape == y.shape


def test_reference_loudness(song):
    quiet_ref = music(6.0, seed=5) * 0.2
    y, _, report = process(song, SR, preset("streaming", match_loudness=True), (quiet_ref, SR))
    assert lufs(y, SR) == pytest.approx(lufs(quiet_ref, SR), abs=0.2)
    assert "eq_db" in report["stages"]["match"]


def test_master_file_writes_results(tmp_path, wav):
    result = master_file(wav, tmp_path / "out", preset("streaming"))
    assert result.output.name == "Bài hát_master.wav"
    assert result.removed.name == "Bài hát_removed.wav"
    report = json.loads((tmp_path / "out" / "Bài hát_report.json").read_text())
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
    assert set(PRESETS) == {"streaming", "loud", "gentle", "clean_only"}
