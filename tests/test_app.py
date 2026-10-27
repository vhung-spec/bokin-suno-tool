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
    assert set(info["presets"]) == {"streaming", "loud", "gentle", "clean_only", "bossa", "jazz"}


def test_master_a_song_end_to_end(client, song, tmp_path):
    settings = client.get("/api/info").json()["presets"]["streaming"]
    settings["eq"]["air"] = 1.0
    files = {"song": ("../../Bài 1.wav", wav_bytes(song[: SR * 4]), "audio/wav"),
             "reference": ("ref.wav", wav_bytes(song[: SR * 4] * 0.5), "audio/wav")}
    res = client.post("/api/jobs", files=files, data={"settings": json.dumps(settings)})
    assert res.status_code == 200, res.text
    job = wait(client, res.json()["id"])
    assert job["state"] == "done", job
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
