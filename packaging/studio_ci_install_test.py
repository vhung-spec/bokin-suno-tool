"""Installs the built Bokin Suno Studio installer for real and checks the installed app (CI, on Windows). (Like
packaging/ci_install_test.py of Bokin Suno Master.)

  python packaging/studio_ci_install_test.py install <BokinSunoStudio-Setup-X.exe>
      a fresh silent install; the installed app starts and serves its page and Lời Đồng Âm; it asks for a key; the
      Suno command line of the installed app runs (suno selftest); setup run again while the app is running closes
      it (BokinSunoStudio.exe --close) and installs over it.

  python packaging/studio_ci_install_test.py update <BokinSunoStudio-Setup-Y.exe> <Y>
      the installed app finds version Y on a stand-in for GitHub (the manifest in the studio-latest release, while
      the API refuses as for an office over its limit of requests, and while the release marked Latest is Bokin Suno
      Master's), downloads and verifies it; "Cập nhật ngay" (POST /api/update/install) installs it and the installer
      starts the app again, now in version Y.

No key is activated on the CI machine: the page, the updates and quitting answer before activation.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Bokin Suno Studio")
EXE = os.path.join(APP_DIR, "BokinSunoStudio.exe")
DATA = os.path.join(os.environ.get("APPDATA", ""), "Bokin", "SunoStudio")
LOG = os.path.join(DATA, "app.log")
RUNNING = os.path.join(DATA, "running.json")
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MANIFEST = "bokin-suno-studio-latest.json"


def running():
    try:
        with open(RUNNING, encoding="utf-8") as f:
            info = json.load(f)
        return int(info["port"]), info["token"]
    except (OSError, ValueError, KeyError):
        return None


def call(path, body=None, token=True):
    found = running()
    if not found:
        return None
    port, tok = found
    data = None if body is None else json.dumps(body).encode()
    headers = {"X-Bokin-Token": tok} if token else {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        with LOCAL.open(urllib.request.Request(f"http://127.0.0.1:{port}{path}", data, headers), timeout=5) as r:
            raw = r.read()
            return json.loads(raw) if r.headers.get_content_type() == "application/json" else raw.decode("utf-8")
    except (OSError, ValueError):
        return None


def stop(message):
    try:
        with open(LOG, encoding="utf-8", errors="replace") as f:
            print("".join(f.readlines()[-60:]))
    except OSError:
        pass
    sys.exit("FAILED: " + message)


def wait(test, seconds, what):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if test():
            print("ok:", what, flush=True)
            return
        time.sleep(1)
    stop(what)


def setup(installer):
    code = subprocess.run([installer, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]).returncode
    if code != 0:
        stop(f"setup ended with code {code}")


def start_app(update_api, update_site=None):
    env = dict(os.environ, BOKIN_NO_BROWSER="1", BOKIN_UPDATE_API=update_api)
    if update_site:
        env["BOKIN_UPDATE_SITE"] = update_site
    return subprocess.Popen([EXE], env=env)


def install(installer):
    setup(installer)
    if not os.path.exists(EXE):
        stop(f"not installed: {EXE}")
    for part in ("loi-dong-am/index.html", "loi-dong-am/engine.js", "suno/bokin_suno.py",
                 "bokin_suno/static/index.html"):
        if not os.path.exists(os.path.join(APP_DIR, "_internal", part)):
            stop(f"not installed: _internal/{part}")
    print("ok: Lời Đồng Âm, the Suno downloader and the Master page are installed", flush=True)
    out = os.path.join(tempfile.mkdtemp(), "suno.txt")
    r = subprocess.run([EXE, "suno", "--data", os.path.join(tempfile.mkdtemp(), "d"), "selftest"],
                       env=dict(os.environ, BOKIN_STUDIO_OUTPUT=out), timeout=300)
    text = open(out, encoding="utf-8", errors="replace").read() if os.path.exists(out) else ""
    print(text.strip())
    if r.returncode != 0 or "selftest OK" not in text:
        stop("the installed app's Suno command line (suno selftest)")
    print("ok: the installed app's Suno command line runs", flush=True)
    app = start_app("http://127.0.0.1:9/none")
    wait(lambda: (call("/api/ping") or {}).get("app") == "bokin-suno-studio", 60, "the installed app answers")
    wait(lambda: "Bokin Suno Studio" in (call("/") or ""), 10, "the installed app serves its page")
    wait(lambda: "Lời Đồng Âm" in (call("/loi-dong-am/index.html", token=False) or ""), 10,
         "the installed app serves Lời Đồng Âm")
    wait(lambda: (call("/api/license") or {}).get("licensed") is False, 10, "it asks for a key (activation screen)")
    setup(installer)
    wait(lambda: app.poll() is not None, 20, "setup closed the running app before installing over it")


def fake_github(installer, version, port):
    """github.com and its API as the update sees them: the release marked Latest is Bokin Suno Master's (its own
    manifest), the Studio's manifest is in the studio-latest release, the API refuses (over its limit)."""
    name, size = os.path.basename(installer), os.path.getsize(installer)
    with open(installer, "rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    manifest = json.dumps({"version": version, "name": name, "size": size, "sha256": sha}).encode()
    master = json.dumps({"version": "9.9.9", "name": "BokinSunoMaster-Setup-9.9.9.exe", "size": 10,
                         "sha256": "0" * 64}).encode()

    class Answer(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print("fake GitHub:", fmt % args, flush=True)

        def reply(self, code, body=b"", headers=()):
            self.send_response(code)
            for k, v in headers:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = self.path.split("?")[0]
            if route == "/limited":
                self.reply(403, b'{"message": "API rate limit exceeded"}', [("X-RateLimit-Remaining", "0")])
            elif route == "/site/releases/latest/download/bokin-suno-master-latest.json":
                self.reply(200, master)
            elif route == f"/site/releases/download/studio-latest/{MANIFEST}":
                self.reply(302, headers=[("Location", f"http://localhost:{port}/blob/{MANIFEST}")])
            elif route == f"/blob/{MANIFEST}":
                self.reply(200, manifest)
            elif route == f"/site/releases/download/studio-v{version}/{name}":
                self.reply(302, headers=[("Location", f"http://localhost:{port}/blob/{name}")])
            elif route == f"/blob/{name}":
                with open(installer, "rb") as f:
                    self.reply(200, f.read(), [("Content-Type", "application/octet-stream")])
            else:
                self.reply(404)

    server = ThreadingHTTPServer(("127.0.0.1", port), Answer)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def update(installer, version):
    fake = fake_github(installer, version, 8798)
    app = start_app("http://127.0.0.1:8798/limited", "http://127.0.0.1:8798/site")
    wait(lambda: (call("/api/update") or {}).get("ready"), 180,
         "the app found the next version, downloaded it and checked it")
    if (call("/api/update") or {}).get("available") != version:
        stop("the app took another release than its own")
    if not (call("/api/update/install", {}) or {}).get("ok"):
        stop("the page could not start the update")
    wait(lambda: app.poll() is not None, 30, "the app closed for the update")
    wait(lambda: (call("/api/ping") or {}).get("version") == version, 240, f"the app runs again, in version {version}")
    call("/api/quit", {})
    fake.shutdown()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "install":
        install(os.path.abspath(sys.argv[2]))
    elif len(sys.argv) >= 4 and sys.argv[1] == "update":
        update(os.path.abspath(sys.argv[2]), sys.argv[3])
    else:
        sys.exit(__doc__)
