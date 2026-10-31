import json

import pytest
import soundfile as sf

from bokin_suno.cli import main
from tests.conftest import SR


def run(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    return exc.value.code


def test_master_and_analyze(tmp_path, song, capsys):
    sf.write(tmp_path / "a.wav", song, SR)
    sf.write(tmp_path / "b.flac", song * 0.5, SR)
    assert run(["master", str(tmp_path), "--out", str(tmp_path / "out"), "--preset", "loud",
                "--deess", "0.3", "--air", "1.5", "--format", "flac"]) == 0
    out = capsys.readouterr().out
    assert "[2/2]" in out and "-10.0 LUFS" in out
    report = json.loads((tmp_path / "out" / "a_report.json").read_text(encoding="utf-8"))
    assert report["settings"]["clean"]["deess"] == 0.3 and report["settings"]["eq"]["air"] == 1.5
    assert run(["analyze", str(tmp_path / "out" / "a_master_To (đã chỉnh).flac"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["lufs"] == pytest.approx(-10, abs=0.15)


def test_errors(tmp_path, capsys):
    assert run(["master", str(tmp_path / "missing.wav"), "--out", str(tmp_path)]) == 1
    assert run(["master", str(tmp_path), "--out", str(tmp_path)]) == 2  # empty folder
    sf.write(tmp_path / "a.wav", [[0.0, 0.0]] * 100, SR)
    assert run(["master", str(tmp_path / "a.wav"), "--lufs", "-60"]) == 2
    assert "error" in capsys.readouterr().err
