"""Bokin Suno Studio's server: the token and host guard, the licence gate, the Suno tasks (with a stand-in for the
Suno command line), the downloaded songs and their lyrics, sending a song to Master."""
import csv
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import music, signed_key

HERE = Path(__file__).resolve().parent
TOKEN = "t0ken"
H = {"X-Bokin-Token": TOKEN}


@pytest.fixture
def client(tmp_path, monkeypatch):
    from bokin_studio import licensing
    from bokin_studio.app import create_app

    monkeypatch.setenv("BOKIN_STUDIO_SUNO_CMD", json.dumps([sys.executable, str(HERE / "stub_suno.py")]))
    monkeypatch.setattr(licensing, "licensed", lambda fresh=False: True)
    app = create_app(TOKEN, port=8776, suno_data=tmp_path / "suno", master_out=tmp_path / "master")
    c = TestClient(app, base_url="http://127.0.0.1:8776")
    c.app_state = app.state
    return c


@pytest.fixture
def gated(tmp_path, monkeypatch):
    """The app as on a computer with no key yet."""
    from bokin_studio.app import create_app

    app = create_app(TOKEN, port=8776, suno_data=tmp_path / "suno", master_out=tmp_path / "master")
    return TestClient(app, base_url="http://127.0.0.1:8776")


def wait_task(client, seconds=20):
    deadline = time.time() + seconds
    while time.time() < deadline:
        task = client.get("/api/suno", headers=H).json()["task"]
        if task and task["state"] != "running":
            return task
        time.sleep(0.1)
    raise AssertionError("the task did not end")


# ---- guard ----

def test_page_and_frames(client):
    page = client.get("/")
    assert page.status_code == 200 and f'"{TOKEN}"' in page.text and "Bokin Suno Studio" in page.text
    assert client.get("/master").status_code == 403
    master = client.get(f"/master?t={TOKEN}")
    assert master.status_code == 200 and "Bokin Suno Master" in master.text and "header { display: none" in master.text
    for name in ("index.html", "engine.js", "hyphen-en-us.js"):
        assert client.get(f"/loi-dong-am/{name}").status_code == 200  # static, nothing of the user: no token
    assert "Lời Đồng Âm" in client.get("/loi-dong-am/index.html").text
    assert client.get("/loi-dong-am/../app.py").status_code in (403, 404)
    assert client.get("/loi-dong-am/x.js", headers=H).status_code == 404


def test_token_and_host(client):
    assert client.get("/api/ping").json()["app"] == "bokin-suno-studio"
    assert client.get("/api/suno").status_code == 403
    assert client.get("/api/suno", headers={"X-Bokin-Token": "nope"}).status_code == 403
    other = TestClient(client.app, base_url="http://evil.example:8776")
    assert other.get("/api/ping").status_code == 403
    assert client.get("/api/suno", headers=H).status_code == 200


@pytest.mark.unlicensed
def test_licence_gate(gated, request):
    from bokin_studio import licensing

    assert gated.get("/api/info", headers=H).status_code == 200
    refused = gated.get("/api/suno", headers=H)
    assert refused.status_code == 403 and refused.json().get("license")
    assert gated.get("/api/library", headers=H).status_code == 403
    assert gated.get("/api/jobs", headers=H).status_code == 403
    bad = gated.post("/api/license", headers=H, json={"key": signed_key(request, ("suno-master",))})
    assert bad.status_code == 400  # a key for Bokin Suno Master does not open the Studio
    ok = gated.post("/api/license", headers=H, json={"key": signed_key(request, ("suno-studio",))})
    assert ok.status_code == 200 and ok.json()["licensed"]
    licensing.status(fresh=True)
    assert gated.get("/api/suno", headers=H).status_code == 200


# ---- Suno tasks ----

def test_list_task(client, tmp_path):
    r = client.post("/api/suno/list", headers=H, json={"account": "suno1", "links": "https://suno.com/create?wid=1\n"})
    assert r.status_code == 200, r.text
    task = wait_task(client)
    assert task["state"] == "done" and [s["title"] for s in task["songs"]] == ["Mưa đêm", "<b>Đậm</b>"]
    assert "Có 2 bài" in "\n".join(task["lines"])
    args = (tmp_path / "suno" / "args.txt").read_text(encoding="utf-8").split("\n")
    assert args == ["list", "suno1", "https://suno.com/create?wid=1"]


def test_download_task_progress_and_options(client, tmp_path):
    folder = tmp_path / "Nhạc"
    r = client.post("/api/suno/download", headers=H, json={
        "account": "suno1", "links": ["https://suno.com/create?wid=1", "https://suno.com/playlist/2"],
        "folder": str(folder), "format": "mp3", "limit": "2", "full": True})
    assert r.status_code == 200, r.text
    task = wait_task(client)
    assert task["state"] == "done" and (task["done"], task["total"]) == (5, 5)
    args = (tmp_path / "suno" / "args.txt").read_text(encoding="utf-8").split("\n")
    assert args == ["download", "suno1", "https://suno.com/create?wid=1", "https://suno.com/playlist/2", "--out",
                    str(folder), "--format", "mp3", "--limit", "2", "--full"]
    # lines are fetched from where the page is
    again = client.get("/api/suno?since=2", headers=H).json()["task"]
    assert again["lines"] == task["lines"][2:]


def test_stop_and_busy(client, monkeypatch):
    monkeypatch.setenv("STUB_PACE", "0.5")
    assert client.post("/api/suno/download", headers=H, json={"account": "suno1", "links": "https://suno.com/x",
                                                             "folder": str(Path.home())}).status_code == 200
    time.sleep(0.8)
    busy = client.post("/api/suno/list", headers=H, json={"account": "suno1", "links": "https://suno.com/x"})
    assert busy.status_code == 409
    assert client.app_state.bokin.busy()
    assert client.post("/api/suno/stop", headers=H, json={}).json()["stopping"]
    task = wait_task(client)
    assert task["state"] == "stopped" and "dừng theo yêu cầu" in "\n".join(task["lines"]) and task["done"] < 5
    assert not client.app_state.bokin.busy()


def test_stop_login(client, monkeypatch):
    monkeypatch.setenv("STUB_LOGIN_WAIT", "60")
    assert client.post("/api/suno/login", headers=H, json={"account": "suno-2"}).status_code == 200
    time.sleep(0.5)
    client.post("/api/suno/stop", headers=H, json={})
    assert wait_task(client)["state"] == "stopped"


@pytest.mark.parametrize("body", [
    {"account": "tài khoản", "links": "https://suno.com/x"},
    {"account": "-x", "links": "https://suno.com/x"},
    {"account": "suno1", "links": ""},
    {"account": "suno1", "links": "--chrome=/bin/sh"},
    {"account": "suno1", "links": "https://suno.com/x", "folder": "relative/folder"},
    {"account": "suno1", "links": "https://suno.com/x", "format": "flac"},
    {"account": "suno1", "links": "https://suno.com/x", "limit": "0"},
])
def test_download_refuses(client, body):
    assert client.post("/api/suno/download", headers=H, json=body).status_code == 400
    assert client.get("/api/suno", headers=H).json()["task"] is None


def test_accounts_listed(client, tmp_path):
    (tmp_path / "suno" / "accounts.json").write_text(json.dumps({"suno1": {"user_id": "u", "added": "2026-10-30"}}),
                                                     encoding="utf-8")
    assert client.get("/api/suno", headers=H).json()["accounts"] == [{"name": "suno1", "added": "2026-10-30"}]


# ---- the downloaded songs ----

def make_folder(folder: Path):
    import soundfile as sf

    folder.mkdir(parents=True)
    sf.write(folder / "Mưa đêm.wav", music(3.0)[:, :2], 48000, subtype="PCM_24")
    (folder / "Mưa đêm.txt").write_text("[Verse]\nSilent night\n<script>x</script>\n", encoding="utf-8")
    (folder / "Không lời.wav").write_bytes(b"RIFF" + bytes(4000))
    (folder / "Secret.wav").write_bytes(b"RIFF" + bytes(4000))  # in the folder, not in the list
    with open(folder / "danh-sach.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ten_bai", "file", "trang_thai", "ghi_chu", "dinh_dang", "link", "luc", "id"])
        w.writerow(["Mưa đêm", "Mưa đêm.wav", "xong", "", "wav", "https://suno.com/song/a", "2026-10-30 10:00:00", "a"])
        w.writerow(["'=Không lời", "Không lời.wav", "xong", "", "wav", "", "2026-10-30 11:00:00", "b"])
        w.writerow(["Lỗi", "", "loi", "Suno chưa cho tải", "wav", "", "2026-10-30 12:00:00", "c"])
        w.writerow(["Thoát", "../../thoat.wav", "xong", "", "wav", "", "2026-10-30 12:00:00", "d"])


def test_library_and_lyrics(client, tmp_path):
    folder = tmp_path / "Nhac"
    make_folder(folder)
    songs = client.get("/api/library", headers=H, params={"folder": str(folder)}).json()["songs"]
    assert [(s["title"], s["lyrics"]) for s in songs] == [("=Không lời", False), ("Mưa đêm", True)]
    lyr = client.get("/api/library/lyrics", headers=H, params={"folder": str(folder), "file": "Mưa đêm.wav"})
    assert lyr.json()["lyrics"].startswith("[Verse]\nSilent night\n<script>")
    assert client.get("/api/library/lyrics", headers=H,
                      params={"folder": str(folder), "file": "Không lời.wav"}).json()["lyrics"] == ""
    for name in ("Secret.wav", "../../thoat.wav", "..", "danh-sach.csv"):
        bad = client.get("/api/library/lyrics", headers=H, params={"folder": str(folder), "file": name})
        assert bad.status_code == 400
    audio = client.get("/api/library/audio", params={"folder": str(folder), "file": "Mưa đêm.wav", "t": TOKEN})
    assert audio.status_code == 200 and audio.content[:4] == b"RIFF"
    assert client.get("/api/library", headers=H, params={"folder": "relative"}).status_code == 400
    assert client.get("/api/library", headers=H, params={"folder": str(tmp_path / "none")}).json()["songs"] == []


def test_send_to_master(client, tmp_path):
    folder = tmp_path / "Nhac"
    make_folder(folder)
    r = client.post("/api/library/master", headers=H, json={"folder": str(folder), "file": "Mưa đêm.wav",
                                                           "preset": "jazz"})
    assert r.status_code == 200, r.text
    job = r.json()["id"]
    deadline = time.time() + 120
    while time.time() < deadline:
        state = client.get(f"/api/jobs/{job}", headers=H).json()
        if state["state"] in ("done", "failed"):
            break
        time.sleep(0.3)
    assert state["state"] == "done", state
    assert state["files"]["master"].endswith("_master.wav")
    got = client.get(f"/api/files/{job}/{state['files']['master']}", headers=H)
    assert got.status_code == 200 and got.content[:4] == b"RIFF"
    assert client.get("/api/jobs", headers=H).json()[0]["id"] == job
    assert client.post("/api/library/master", headers=H, json={"folder": str(folder), "file": "Mưa đêm.wav",
                                                              "preset": "nope"}).status_code == 400
    assert client.post("/api/library/master", headers=H, json={"folder": str(folder),
                                                              "file": "Secret.wav"}).status_code == 400


def test_settings_kept(client):
    client.post("/api/settings", headers=H, json={"account": "suno1", "links": "https://suno.com/x", "evil": 1,
                                                 "folder": 5})
    s = client.get("/api/settings", headers=H).json()
    assert s == {"account": "suno1", "links": "https://suno.com/x"}


def test_shutdown_ends_a_task(client, monkeypatch):
    monkeypatch.setenv("STUB_LOGIN_WAIT", "60")
    client.post("/api/suno/login", headers=H, json={"account": "suno1"})
    time.sleep(0.5)
    assert client.post("/api/quit", headers=H, json={}).json() == {"busy": True}
    client.post("/api/shutdown", headers=H)
    assert wait_task(client)["state"] == "stopped"
