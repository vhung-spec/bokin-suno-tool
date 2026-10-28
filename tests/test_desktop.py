import json
import threading
import time
import urllib.request

import pytest

pytest.importorskip("uvicorn")
from bokin_suno import desktop, paths  # noqa: E402


def wait_for(test, seconds=20):
    deadline = time.time() + seconds
    while time.time() < deadline:
        value = test()
        if value:
            return value
        time.sleep(0.2)
    raise AssertionError("timed out")


def test_one_copy_runs_and_the_installer_can_close_it():
    assert desktop.close_running() == 0  # nothing running: nothing to do
    done = []
    thread = threading.Thread(target=lambda: done.append(desktop.serve(idle_exit=False)), daemon=True)
    thread.start()
    info = wait_for(desktop.running)
    assert info["port"] in paths.PORTS
    saved = json.loads(paths.running_file().read_text(encoding="utf-8"))
    assert saved["token"] == info["token"] and saved["port"] == info["port"]
    page = urllib.request.urlopen(f"http://127.0.0.1:{info['port']}/", timeout=5).read().decode()
    assert info["token"] in page

    assert desktop.close_running() == 0  # what the installer runs before replacing the files
    thread.join(20)
    assert done == [0] and not thread.is_alive()
    assert not paths.running_file().exists() and desktop.running() is None


def test_a_busy_app_tells_the_installer_to_wait(monkeypatch):
    from bokin_suno import app as app_mod

    monkeypatch.setattr(app_mod.Jobs, "busy", lambda self: True)
    thread = threading.Thread(target=lambda: desktop.serve(idle_exit=False), daemon=True)
    thread.start()
    info = wait_for(desktop.running)
    assert desktop.close_running() == desktop.BUSY
    assert thread.is_alive()
    req = urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/shutdown", data=b"{}", method="POST",
                                 headers={"X-Bokin-Token": info["token"], "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=5).read()
    thread.join(20)
    assert not thread.is_alive()


def test_dev_builds_never_update_themselves():
    assert paths.version() == "dev" or (paths.package_dir() / "version.txt").exists()
    from bokin_suno import updater

    assert updater.parse_version("dev") is None
