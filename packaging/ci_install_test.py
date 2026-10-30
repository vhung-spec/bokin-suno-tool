"""Installs the built installer for real and checks the installed app (CI, on Windows). (Like Bokin FX's.)

  python packaging/ci_install_test.py install <BokinSunoMaster-Setup-X.exe>
      a fresh silent install; the installed app starts and serves its page; setup run again while the app is
      running closes it (BokinSunoMaster.exe --close) and installs over it.

  python packaging/ci_install_test.py update <BokinSunoMaster-Setup-Y.exe> <Y>
      the installed app finds version Y on a stand-in for GitHub (in the newest release's manifest, while the API
      refuses as for an office over its limit of requests), downloads and verifies it; "Cập nhật ngay"
      (POST /api/update/install) installs it and the installer starts the app again, now in version Y.

No key is activated on the CI machine: the page, the updates and quitting answer before activation.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fake_releases  # noqa: E402

EXE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Bokin Suno Master", "BokinSunoMaster.exe")
DATA = os.path.join(os.environ.get("APPDATA", ""), "Bokin", "SunoMaster")
LOG = os.path.join(DATA, "app.log")
RUNNING = os.path.join(DATA, "running.json")
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def running():
    """(port, token) of the running app, from the file it writes, or None."""
    try:
        with open(RUNNING, encoding="utf-8") as f:
            info = json.load(f)
        return int(info["port"]), info["token"]
    except (OSError, ValueError, KeyError):
        return None


def call(path, body=None):
    found = running()
    if not found:
        return None
    port, token = found
    data = None if body is None else json.dumps(body).encode()
    headers = {"X-Bokin-Token": token}
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
    app = start_app("http://127.0.0.1:9/none")
    wait(lambda: (call("/api/ping") or {}).get("app") == "bokin-suno-master", 60, "the installed app answers")
    wait(lambda: "Bokin Suno Master" in (call("/") or ""), 10, "the installed app serves its page")
    wait(lambda: (call("/api/license") or {}).get("licensed") is False, 10, "it asks for a key (activation screen)")
    setup(installer)
    wait(lambda: app.poll() is not None, 20, "setup closed the running app before installing over it")


def update(installer, version):
    fake = fake_releases.serve(f"app-v{version}", installer, 8799)
    # the newest release's manifest, while the API refuses as it does for an office over its limit of requests
    app = start_app("http://127.0.0.1:8799/limited", "http://127.0.0.1:8799/site")
    wait(lambda: (call("/api/update") or {}).get("ready"), 180,
         "the app found the next version, downloaded it and checked it")
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
