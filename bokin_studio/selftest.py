"""BokinSunoStudio.exe --selftest: checks a build from end to end, then quits (0: all good).

CI runs it on the built app before making the installer:
- mastering (Bokin Suno Master's own self-test of the mastering: every output format, loudness, true peak), so
  numpy, scipy, soundfile and its libsndfile made it into the bundle;
- the Suno side: the command line's own self-test run as the app runs it (BokinSunoStudio.exe suno selftest, its
  output in a file), so suno/, patchright and its driver made it in;
- the real server: the page, Lời Đồng Âm and the Master page served, the licence gate walked with a test key (the
  API refused before activation, a key not signed by the seller refused, a key for Bokin Suno Master refused, a key
  for this app and computer opens it), the downloaded songs of a folder listed with their lyrics.
The user's own keys and settings are never touched (a temporary key store and data folder).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def run() -> int:
    from bokin_studio import paths

    results = []

    def check(name: str, ok) -> None:
        results.append(bool(ok))
        print(("ok: " if ok else "FAILED: ") + name, flush=True)

    print(f"Bokin Suno Studio {paths.version()} self-test", flush=True)
    work = tempfile.mkdtemp(prefix="bokin-studio-selftest-")
    os.environ["BOKIN_STUDIO_DATA"] = os.path.join(work, "data")
    os.environ["BOKIN_STUDIO_OUT"] = os.path.join(work, "out")
    try:
        _check_master(check)
        _check_suno(work, check)
        _check_server(work, check)
    except Exception:  # noqa: BLE001 - a crash is a failed test, with its traceback in the log
        import traceback
        traceback.print_exc()
        results.append(False)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    ok = bool(results) and all(results)
    print("self-test " + ("passed" if ok else "FAILED"), flush=True)
    return 0 if ok else 1


def _check_master(check) -> None:
    from bokin_suno import audio_io
    from bokin_suno.analysis import lufs, true_peak_db
    from bokin_suno.master import master_file, preset
    from bokin_suno.selftest import _song

    work = tempfile.mkdtemp(prefix="bokin-studio-master-")
    try:
        sr = 48000
        song = os.path.join(work, "Bài thử.wav")
        audio_io.save(song, _song(sr), sr, "wav", 24)
        for name, fmt, bits, rate in (("jazz", "flac", 16, 44100), ("streaming", "mp3", 24, None)):
            settings = preset(name, format=fmt, bits=bits, sample_rate=rate)
            result = master_file(song, os.path.join(work, name), settings)
            y, out_sr = audio_io.load(result.output)
            loud, peak = lufs(y, out_sr), true_peak_db(y)
            check(f"master {name}: {result.output.name}, {loud:.2f} LUFS, {peak:.2f} dBTP",
                  out_sr == (rate or sr) and abs(loud + 14) < (0.6 if fmt == "mp3" else 0.25)
                  and peak <= settings.ceiling_db + (0.3 if fmt == "mp3" else 0.02))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _check_suno(work, check) -> None:
    from bokin_studio.suno_tasks import suno_command

    out = os.path.join(work, "suno-selftest.txt")
    env = dict(os.environ, BOKIN_STUDIO_OUTPUT=out)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    r = subprocess.run(suno_command() + ["--data", os.path.join(work, "suno"), "selftest"], env=env,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=flags, timeout=300)
    text = open(out, encoding="utf-8", errors="replace").read() if os.path.exists(out) else ""
    print(text.strip(), flush=True)
    check("the Suno command line runs (suno selftest)", r.returncode == 0 and "selftest OK" in text)
    from patchright._impl._driver import compute_driver_executable

    driver = compute_driver_executable()
    check(f"patchright's driver is in the bundle: {driver[0]}", all(os.path.exists(p) for p in driver))


def _check_server(work, check) -> None:
    import socket

    import uvicorn

    from bokin_license import ed25519, keys, store
    from bokin_studio import licensing
    from bokin_studio.app import create_app

    kept = keys.PUBLIC_KEY, store.default_folder
    store.default_folder = lambda: os.path.join(work, "license")  # never the user's own keys
    try:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(16)
        port = sock.getsockname()[1]
        token = "selftest"
        app = create_app(token, port=port, desktop=False)
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, log_level="warning"))
        threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
        base = f"http://127.0.0.1:{port}"

        def call(path, body=None):
            data = None if body is None else json.dumps(body).encode()
            headers = {"X-Bokin-Token": token, "Content-Type": "application/json"}
            try:
                with LOCAL.open(urllib.request.Request(base + path, data, headers), timeout=10) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        deadline = time.time() + 20
        while time.time() < deadline and call("/api/ping")[0] != 200:
            time.sleep(0.2)
        status, page = call("/")
        check("server: the page is served", status == 200 and b"Bokin Suno Studio" in page)
        status, page = call("/loi-dong-am/index.html")
        check("server: Lời Đồng Âm is served", status == 200 and "Lời Đồng Âm".encode() in page
              and call("/loi-dong-am/engine.js")[0] == 200 and call("/loi-dong-am/hyphen-en-us.js")[0] == 200)
        licensing.status(fresh=True)
        check("server: refuses the Suno side before activation", call("/api/suno")[0] == 403)
        machine = licensing.view()["machine"]
        secret = os.urandom(32)
        status, _ = call("/api/license", {"key": keys.make_key(secret, machine, ["suno-studio"])})
        check("server: a key not from the seller is refused", status == 400)
        keys.PUBLIC_KEY = ed25519.public_key(secret)
        status, _ = call("/api/license", {"key": keys.make_key(secret, machine, ["suno-master"])})
        check("server: a key for Bokin Suno Master is refused", status == 400)
        status, _ = call("/api/license", {"key": keys.make_key(secret, machine, ["suno-studio"])})
        check("server: a key for this computer activates the app", status == 200)
        status, body = call("/api/suno")
        check("server: the Suno side answers once activated", status == 200 and "accounts" in json.loads(body))
        status, page = call(f"/master?t={token}")
        check("server: the Master page is served", status == 200 and b"Bokin Suno Master" in page)
        folder = os.path.join(work, "Nhạc")
        os.makedirs(folder)
        with open(os.path.join(folder, "Bài.wav"), "wb") as f:
            f.write(b"RIFF" + bytes(2000))
        with open(os.path.join(folder, "Bài.txt"), "w", encoding="utf-8") as f:
            f.write("[Verse]\nline\n")
        with open(os.path.join(folder, "danh-sach.csv"), "w", encoding="utf-8-sig", newline="") as f:
            f.write("ten_bai,file,trang_thai,ghi_chu,dinh_dang,link,luc,id\r\nBài,Bài.wav,xong,,wav,,2026-10-30,x\r\n")
        status, body = call("/api/library?" + urllib.parse.urlencode({"folder": folder}))
        songs = json.loads(body).get("songs", []) if status == 200 else []
        check("server: the downloaded songs and their lyrics", [(s["title"], s["lyrics"]) for s in songs]
              == [("Bài", True)])
        server.should_exit = True
    finally:
        keys.PUBLIC_KEY, store.default_folder = kept
        licensing.status(fresh=True)


if __name__ == "__main__":
    sys.exit(run())
