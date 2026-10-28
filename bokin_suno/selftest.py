"""BokinSunoMaster.exe --selftest: checks a build from end to end, then quits (0: all good).

CI runs it on the built app before making the installer. It masters a made-up song with every
output format (so numpy, scipy, soundfile and its libsndfile made it into the bundle), checks
loudness and true peak, then starts the real server and walks the activation screen with a test
key: the API is refused before activation, a key not signed by the seller is refused, a key for
this computer opens the app. The user's own keys and settings are never touched (a temporary
key store and data folder).
"""

import json
import os
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.request

import numpy as np

LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _song(sr: int = 48000, seconds: float = 8.0) -> np.ndarray:
    """Chords, a bass line, kick and hat: enough for every stage to have work."""
    rng = np.random.default_rng(1)
    t = np.arange(int(sr * seconds)) / sr
    x = np.zeros((len(t), 2))
    for i, root in enumerate((220.0, 196.0, 174.6, 246.9)):
        part = (t >= 2 * i) & (t < 2 * i + 2)
        env = np.exp(-(t - 2 * i) * 0.8) * part
        for h in range(1, 8):
            x[:, 0] += 0.05 / h * env * np.sin(2 * np.pi * root * h * t)
            x[:, 1] += 0.05 / h * env * np.sin(2 * np.pi * root * h * t + 0.3)
    x += (0.15 * np.sin(2 * np.pi * 55 * t))[:, None]
    for k in np.arange(0, seconds, 0.5):
        a = int(k * sr)
        m = min(len(t) - a, int(0.2 * sr))
        tt = np.arange(m) / sr
        x[a:a + m] += (0.5 * np.sin(2 * np.pi * (50 + 80 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12))[:, None]
    x += rng.standard_normal(x.shape) * 0.003
    return x


def run() -> int:
    from bokin_suno import audio_io, paths
    from bokin_suno.analysis import lufs, true_peak_db
    from bokin_suno.master import master_file, preset

    results = []

    def check(name: str, ok) -> None:
        results.append(bool(ok))
        print(("ok: " if ok else "FAILED: ") + name, flush=True)

    print(f"Bokin Suno Master {paths.version()} self-test", flush=True)
    work = tempfile.mkdtemp(prefix="bokin-suno-selftest-")
    try:
        sr = 48000
        song = os.path.join(work, "Bài thử.wav")
        audio_io.save(song, _song(sr), sr, "wav", 24)
        for name, fmt, bits, rate in (("bossa", "wav", 24, None), ("jazz", "flac", 16, 44100),
                                      ("streaming", "mp3", 24, None)):
            settings = preset(name, format=fmt, bits=bits, sample_rate=rate)
            result = master_file(song, os.path.join(work, name), settings)
            y, out_sr = audio_io.load(result.output)
            check(f"{name}: wrote {result.output.name} at {out_sr} Hz", out_sr == (rate or sr))
            loud, peak = lufs(y, out_sr), true_peak_db(y)
            check(f"{name}: {loud:.2f} LUFS (target -14)", abs(loud + 14) < (0.6 if fmt == "mp3" else 0.25))
            check(f"{name}: true peak {peak:.2f} dBTP", peak <= settings.ceiling_db + (0.3 if fmt == "mp3" else 0.02))
            check(f"{name}: report and removed artifacts written",
                  result.removed is not None and result.removed.exists()
                  and (result.output.parent / "Bài thử_report.json").exists())
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


def _check_server(work: str, check) -> None:
    """The real server on a free port: the page, the licence gate, activation with a test key."""
    import socket

    import uvicorn

    from bokin_license import ed25519, keys, store
    from bokin_suno import licensing
    from bokin_suno.app import create_app

    kept = keys.PUBLIC_KEY, store.default_folder
    store.default_folder = lambda: os.path.join(work, "license")  # never the user's own keys
    try:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(16)
        port = sock.getsockname()[1]
        token = "selftest"
        app = create_app(token, os.path.join(work, "out"), port=port, desktop=False)
        server = uvicorn.Server(uvicorn.Config(app, log_config=None, log_level="warning"))
        threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
        base = f"http://127.0.0.1:{port}"

        def call(path, body=None):
            data = None if body is None else json.dumps(body).encode()
            headers = {"X-Bokin-Token": token, "Content-Type": "application/json"}
            req = urllib.request.Request(base + path, data, headers)
            try:
                with LOCAL.open(req, timeout=10) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        deadline = time.time() + 20
        while time.time() < deadline and call("/api/ping")[0] != 200:
            time.sleep(0.2)
        status, page = call("/")
        check("server: the page is served", status == 200 and b"Bokin Suno Master" in page)
        licensing.status(fresh=True)
        check("server: refuses to master before activation", call("/api/jobs")[0] == 403)
        machine = licensing.view()["machine"]
        secret = os.urandom(32)
        status, _ = call("/api/license", {"key": keys.make_key(secret, machine, ["suno-master"])})
        check("server: a key not from the seller is refused", status == 400)
        keys.PUBLIC_KEY = ed25519.public_key(secret)
        status, _ = call("/api/license", {"key": keys.make_key(secret, machine, ["fx"])})
        check("server: a key for another Bokin app is refused", status == 400)
        status, _ = call("/api/license", {"key": keys.make_key(secret, machine, ["suno-master"])})
        check("server: a key for this computer activates the app", status == 200)
        check("server: the app answers once activated", call("/api/jobs")[0] == 200)
        server.should_exit = True
    finally:
        keys.PUBLIC_KEY, store.default_folder = kept
        licensing.status(fresh=True)
