"""Bokin Suno Studio's updates live beside Bokin Suno Master's in the same repository: neither app may ever take the
other's release. The Studio reads the manifest of its own studio-latest release, never the release GitHub marks
"Latest" (Bokin Suno Master's)."""
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from bokin_studio import updater
from bokin_suno import updater as master_updater

INSTALLER = b"MZ" + bytes(5000)
SHA = hashlib.sha256(INSTALLER).hexdigest()


@pytest.fixture
def github():
    """A stand-in for github.com and its API: Bokin Suno Master's release is "Latest", the Studio's are not."""
    hits = []
    state = {"manifests": True, "base": ""}
    studio = {"version": "1.0.9", "name": "BokinSunoStudio-Setup-1.0.9.exe", "size": len(INSTALLER), "sha256": SHA}
    master = {"version": "1.0.20", "name": "BokinSunoMaster-Setup-1.0.20.exe", "size": len(INSTALLER), "sha256": SHA}

    def asset(name):
        return {"name": name, "size": len(INSTALLER), "digest": f"sha256:{SHA}",
                "browser_download_url": f"/site/releases/download/x/{name}"}

    listing = [
        {"tag_name": "app-v1.0.20", "draft": False, "prerelease": False, "assets": [asset(master["name"])]},
        {"tag_name": "studio-v1.0.9", "draft": False, "prerelease": False, "assets": [asset(studio["name"])]},
        {"tag_name": "studio-latest", "draft": False, "prerelease": False,
         "assets": [asset("BokinSunoStudio-Setup.exe")]},
    ]

    class Answer(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, body=b""):
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            hits.append(self.path)
            if self.path == "/api":
                return self.reply(200, json.dumps(listing).replace('"/site/', f'"{state["base"]}/site/').encode())
            if state["manifests"] and self.path == f"/site/releases/download/studio-latest/{updater.MANIFEST}":
                return self.reply(200, json.dumps(studio).encode())
            if state["manifests"] and self.path == f"/site/releases/latest/download/{master_updater.MANIFEST}":
                return self.reply(200, json.dumps(master).encode())
            if self.path.startswith("/site/releases/download/"):
                return self.reply(200, INSTALLER)
            return self.reply(404)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Answer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state["base"] = f"http://127.0.0.1:{server.server_address[1]}"
    state["hits"] = hits
    yield state
    server.shutdown()


def use(monkeypatch, github):
    monkeypatch.setenv("BOKIN_UPDATE_API", github["base"] + "/api")
    monkeypatch.setenv("BOKIN_UPDATE_SITE", github["base"] + "/site")


def test_names_never_meet():
    assert updater.MANIFEST != master_updater.MANIFEST
    assert not updater.TAG.startswith(master_updater.TAG) and not master_updater.TAG.startswith(updater.TAG)
    assert not updater.CHANNEL.startswith(master_updater.TAG) and not updater.CHANNEL.startswith(updater.TAG)
    assert not updater.INSTALLER.match("BokinSunoMaster-Setup-1.0.9.exe")
    assert not master_updater.INSTALLER.match("BokinSunoStudio-Setup-1.0.9.exe")
    assert not updater.INSTALLER.match("BokinSunoStudio-Setup.exe")  # the guide's fixed-name copy


def test_studio_reads_its_own_manifest(monkeypatch, github):
    use(monkeypatch, github)
    release = updater.latest()
    assert release.version == "1.0.9" and release.name == "BokinSunoStudio-Setup-1.0.9.exe"
    assert release.url.endswith("/releases/download/studio-v1.0.9/BokinSunoStudio-Setup-1.0.9.exe")
    assert not any("/releases/latest/" in h for h in github["hits"]), "the Studio never reads the Latest release"


def test_master_unaffected(monkeypatch, github):
    use(monkeypatch, github)
    assert master_updater.latest().name == "BokinSunoMaster-Setup-1.0.20.exe"
    github["manifests"] = False  # from the API's list: each takes only its own tags
    assert master_updater.latest().version == "1.0.20"
    assert updater.latest().version == "1.0.9"


def test_update_downloads_and_checks(monkeypatch, github, tmp_path):
    use(monkeypatch, github)
    up = updater.AutoUpdate("1.0.8", str(tmp_path / "updates"))
    up.check()
    assert up.state["ready"] and up.state["available"] == "1.0.9"
    assert open(up.installer, "rb").read() == INSTALLER
    same = updater.AutoUpdate("1.0.9", str(tmp_path / "updates2"))
    same.check()
    assert not same.state["ready"] and same.state["error"] is None
