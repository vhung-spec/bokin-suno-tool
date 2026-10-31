import io
import json
import time

import pytest
import soundfile as sf

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from bokin_suno import app as app_mod  # noqa: E402
from tests.conftest import SR  # noqa: E402

TOKEN = "test-token"


@pytest.fixture
def client(tmp_path):
    app = app_mod.create_app(TOKEN, tmp_path / "out", extra_hosts=("testserver",))
    return TestClient(app, headers={"X-Bokin-Token": TOKEN})


def wav_bytes(x):
    buf = io.BytesIO()
    sf.write(buf, x, SR, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def wait(client, job_id, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] not in ("queued", "running"):
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def test_page_embeds_token_and_api_needs_it(client):
    assert TOKEN in client.get("/").text
    anonymous = TestClient(client.app)
    assert anonymous.get("/api/info").status_code == 403
    assert anonymous.get("/api/info", headers={"X-Bokin-Token": "wrong"}).status_code == 403
    assert client.get("/api/info", headers={"Host": "evil.example"}).status_code == 403
    info = client.get("/api/info").json()
    assert set(info["presets"]) == {"streaming", "loud", "gentle", "clean_only", "bossa", "jazz", "dark_piano",
                                    "classical_christmas"}


def test_master_a_song_end_to_end(client, song, tmp_path):
    settings = client.get("/api/info").json()["presets"]["streaming"]
    settings["eq"]["air"] = 1.0
    files = {"song": ("../../Bài 1.wav", wav_bytes(song[: SR * 4]), "audio/wav"),
             "reference": ("ref.wav", wav_bytes(song[: SR * 4] * 0.5), "audio/wav")}
    res = client.post("/api/jobs", files=files, data={"settings": json.dumps(settings), "preset": "streaming"})
    assert res.status_code == 200, res.text
    job = wait(client, res.json()["id"])
    assert job["state"] == "done", job
    # the kiểu master: shown, and in the master's file name (the Độ sáng slider moved: "đã chỉnh")
    assert job["style"] == {"preset": "streaming", "custom": True, "label": "Nghe trực tuyến (đã chỉnh)"}
    assert job["files"]["master"] == "Bài 1_master_Nghe trực tuyến (đã chỉnh).wav"
    # the compare player's waveforms
    peaks = client.get(f"/api/peaks/{job['id']}/{job['files']['master']}").json()
    assert peaks["seconds"] == pytest.approx(4, abs=0.01) and len(peaks["peaks"]) == 2 * 1200
    assert all(-1.01 <= v <= 1.01 for v in peaks["peaks"]) and max(peaks["peaks"]) > 0.05
    assert client.get(f"/api/peaks/{job['id']}/settings.json").status_code == 404
    assert job["song"] == "Bài 1.wav" and job["reference"] == "ref_ref.wav"
    assert set(job["files"]) == {"source", "master", "removed"}
    assert job["report"]["output"]["lufs"] == pytest.approx(-14, abs=0.2)
    audio = client.get(f"/api/files/{job['id']}/{job['files']['master']}")
    assert audio.status_code == 200 and audio.content[:4] == b"RIFF"
    dl = client.get(f"/api/files/{job['id']}/{job['files']['master']}?download=true")
    assert "attachment" in dl.headers["content-disposition"]
    assert client.get(f"/api/files/{job['id']}/settings.json").status_code == 404
    assert client.get(f"/api/files/{job['id']}/..%2F..%2Fx").status_code == 404

    # the list survives a restart: it is read back from the folders
    again = TestClient(app_mod.create_app(TOKEN, tmp_path / "out", extra_hosts=("testserver",)),
                       headers={"X-Bokin-Token": TOKEN})
    listed = again.get("/api/jobs").json()
    assert [j["id"] for j in listed] == [job["id"]] and listed[0]["state"] == "done"
    assert listed[0]["style"] == job["style"]
    assert again.delete(f"/api/jobs/{job['id']}").status_code == 200
    assert again.get("/api/jobs").json() == []


def test_bad_settings_and_files(client, song):
    files = {"song": ("a.wav", wav_bytes(song[:SR]), "audio/wav")}
    assert client.post("/api/jobs", files=files, data={"settings": '{"target_lufs": 5}'}).status_code == 400
    assert client.post("/api/jobs", files=files, data={"settings": "not json"}).status_code == 400
    exe = {"song": ("a.exe", b"MZ", "application/octet-stream")}
    assert client.post("/api/jobs", files=exe, data={"settings": "{}"}).status_code == 400


def test_a_broken_file_fails_cleanly(client):
    res = client.post("/api/jobs", files={"song": ("x.wav", b"not audio", "audio/wav")},
                      data={"settings": "{}"})
    job = wait(client, res.json()["id"])
    assert job["state"] == "failed" and job["error"]


def test_every_preset_fits_the_page_controls():
    # a value a control cannot show is silently changed when the page sends it
    # back (a select without the option reads "", that is 0: off)
    import re
    from pathlib import Path

    from bokin_suno.master import PRESETS, preset

    page = (Path(app_mod.__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    inputs = {m["id"]: m for m in re.finditer(r'<input type="(?:range|number)" id="(?P<id>\w+)" min="(?P<min>[-\d.]+)"'
                                              r' max="(?P<max>[-\d.]+)" step="(?P<step>[\d.]+)"', page)}
    select = re.search(r'<select id="mono_bass_hz">(.*?)</select>', page, re.S)[1]
    options = {float(v) for v in re.findall(r'<option value="([-\d.]+)">', select)}
    assert inputs and options
    for name in PRESETS:
        s = preset(name).to_dict()
        values = {**s, **s["clean"], **s["eq"]}
        assert s["mono_bass_hz"] in options, (name, "mono_bass_hz")
        for key, m in inputs.items():
            value = values[key]
            if value is None:  # target_lufs None: "keep the loudness" is ticked instead
                continue
            low, high, step = float(m["min"]), float(m["max"]), float(m["step"])
            assert low <= value <= high, (name, key, value)
            assert abs((value - low) / step - round((value - low) / step)) < 1e-6, (name, key, value)


def test_kiểu_master_of_songs_mastered_before(tmp_path):
    """A song mastered before the kiểu master was kept: told by its settings."""
    from bokin_suno.master import preset

    for name, settings in (("20261028-100000-a", preset("bossa").to_dict()),
                           ("20261028-100001-b", {**preset("jazz").to_dict(), "warmth": 0.9})):
        d = tmp_path / "out" / name
        d.mkdir(parents=True)
        (d / "settings.json").write_text(json.dumps({"song": "a.wav", "reference": None, "settings": settings}),
                                         encoding="utf-8")
    c = TestClient(app_mod.create_app(TOKEN, tmp_path / "out", extra_hosts=("testserver",)),
                   headers={"X-Bokin-Token": TOKEN})
    styles = {j["id"]: j["style"]["label"] for j in c.get("/api/jobs").json()}
    assert styles == {"20261028-100000-a": "Bossa nova", "20261028-100001-b": "Tuỳ chỉnh"}
