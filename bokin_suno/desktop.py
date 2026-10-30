"""Bokin Suno Master on a computer: one local server, the page in a window of its own, updates,
and quitting by itself. (Built like Bokin FX's fx/app.py.)

- One copy runs at a time for each user (a named mutex on Windows, a lock file elsewhere): a
  second start only opens a window on the running one, waiting for it if it is still starting.
- The window is Edge (or Chrome) in app mode (--app=<url>): no tabs or address bar. Under WSL the
  Windows browser opens; elsewhere the default browser.
- The installed app quits when no page has asked anything for a while (its window was closed) and
  no song is being mastered, installing a downloaded update on the way out. "Cập nhật ngay" on the
  page installs at once and the installer starts the app again; the open window reconnects.
- The installer first runs the installed exe with --close: it asks a running app to quit (through
  /api/quit, with the token from running.json) and answers 3 while a song is being mastered (setup
  then stops with a message).
"""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

from bokin_suno import paths, updater

IDLE_EXIT = 300  # seconds without the page, then the installed app quits
BUSY = 3  # exit code of --close while the running app is mastering a song
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # this PC itself: never via a proxy
_guard = None  # the single-instance mutex (or lock file), held for the life of the process


def log_to_file() -> None:
    """An installed app has no console: what it prints goes to app.log in the data folder."""
    path = paths.log_path()
    try:
        if path.exists() and path.stat().st_size > 2_000_000:
            os.replace(path, str(path) + ".old")
    except OSError:
        pass
    sys.stdout = sys.stderr = open(path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 - for the app's life


def ping(port: int, timeout: float = 1.0) -> dict | None:
    try:
        with LOCAL.open(f"http://127.0.0.1:{port}/api/ping", timeout=timeout) as r:
            return json.loads(r.read())
    except (OSError, ValueError):
        return None


def running() -> dict | None:
    """{"port", "token"} of this user's running Bokin Suno Master, or None."""
    try:
        info = json.loads(paths.running_file().read_text(encoding="utf-8"))
        port, token = int(info["port"]), str(info["token"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    answer = ping(port)
    if answer and answer.get("app") == paths.APP_ID and answer.get("owner") == paths.owner():
        return {"port": port, "token": token}
    return None


def first_copy() -> bool:
    """True for the first copy of the app started by this user; later ones see the guard taken."""
    global _guard
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        _guard = kernel32.CreateMutexW(None, False, f"Local\\BokinSunoMaster-{paths.owner()}")
        return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS
    import fcntl
    _guard = open(paths.data_dir() / "app.lock", "w")  # noqa: SIM115 - held while running
    try:
        fcntl.flock(_guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def close_running(wait: float = 20) -> int:
    """--close, for the installer: a running Bokin Suno Master is asked to quit. 0 once none runs,
    BUSY if it is mastering a song."""
    info = running()
    if info is None:
        return 0
    req = urllib.request.Request(f"http://127.0.0.1:{info['port']}/api/quit", data=b"{}", method="POST",
                                 headers={"X-Bokin-Token": info["token"], "Content-Type": "application/json"})
    try:
        with LOCAL.open(req, timeout=5) as r:
            if json.loads(r.read()).get("busy"):
                return BUSY
    except (OSError, ValueError):
        pass
    deadline = time.time() + wait
    while time.time() < deadline and ping(info["port"]):
        time.sleep(0.3)
    return 0


def _wsl() -> bool:
    try:
        return "microsoft" in open("/proc/version", encoding="utf-8").read().lower()  # noqa: SIM115
    except OSError:
        return False


def show(url: str) -> None:
    """The page in its own window: Edge or Chrome in app mode, else the default browser."""
    if os.environ.get("BOKIN_NO_BROWSER"):
        return
    if os.name == "nt":
        bases = [os.environ.get(k) for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
        for exe in (r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe"):
            for base in filter(None, bases):
                path = os.path.join(base, exe)
                if os.path.exists(path):
                    subprocess.Popen([path, f"--app={url}", "--window-size=1280,900"])
                    return
    elif _wsl():  # the Windows browser reaches WSL's localhost
        subprocess.Popen(["explorer.exe", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    webbrowser.open(url)


def _bind() -> socket.socket | None:
    """A listening socket on the first free port of paths.PORTS."""
    for port in paths.PORTS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if os.name == "nt":  # never share a port another program holds
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            sock.listen(64)
            return sock
        except OSError:
            sock.close()
    return None


def _write_running(port: int, token: str) -> None:
    path = paths.running_file()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"port": port, "token": token, "pid": os.getpid(), "version": paths.version()}, f)


def _forget_running(token: str) -> None:
    try:
        if json.loads(paths.running_file().read_text(encoding="utf-8")).get("token") == token:
            paths.running_file().unlink()
    except (OSError, ValueError):
        pass


def serve(out_dir=None, updated: bool = False, idle_exit: bool | None = None) -> int:
    """Runs the app until it is asked to quit (or, installed, until its window has been gone a while)."""
    import uvicorn

    from bokin_suno.app import create_app

    if not first_copy():  # another copy is running, or still starting: show it once it answers
        deadline = time.time() + 40
        while time.time() < deadline:
            info = running()
            if info:
                show(f"http://127.0.0.1:{info['port']}/")
                return 0
            time.sleep(0.5)
        return 0
    sock = _bind()
    if sock is None:
        print(f"no free port in {paths.PORTS.start}-{paths.PORTS.stop - 1}", flush=True)
        return 1
    port = sock.getsockname()[1]
    token = secrets.token_urlsafe(24)
    app = create_app(token, out_dir or paths.out_dir(), port=port, desktop=True)
    shared, jobs = app.state.bokin, app.state.jobs
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, log_level="warning", access_log=False))
    shared.server = server
    _write_running(port, token)
    url = f"http://127.0.0.1:{port}/"
    print(f"Bokin Suno Master {paths.version()} at {url}; results in {jobs.dir}", flush=True)
    if updater.parse_version(paths.version()):
        shared.updater = updater.AutoUpdate(paths.version(), str(paths.updates_dir())).start()
    if idle_exit is None:
        idle_exit = paths.frozen()
    started = time.time()
    idle = threading.Event()
    if not updated:
        show(url)

    def watch():
        shown = not updated
        while not shared.quit.wait(2):
            if not shown and time.time() - started > 10:
                shown = True
                if shared.seen <= started:  # no window came back after the update: open one
                    show(url)
            if idle_exit and time.time() - shared.seen > IDLE_EXIT and not jobs.busy():
                print("no page for a while: quitting", flush=True)
                idle.set()
                shared.stop()

    threading.Thread(target=watch, daemon=True, name="watch").start()
    try:
        server.run(sockets=[sock])
    finally:
        _forget_running(token)
    up = shared.updater
    if up and up.state.get("ready"):
        if shared.relaunch:
            up.run_installer(restart=True)
        elif idle.is_set():
            up.run_installer(restart=False)
    print("quitting", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="BokinSunoMaster")
    ap.add_argument("--selftest", action="store_true", help="master a test song, check the licence screen, quit")
    ap.add_argument("--updated", action="store_true", help="started again by the installer after an update")
    ap.add_argument("--close", action="store_true", help="ask a running Bokin Suno Master to quit (installer)")
    args = ap.parse_args(argv)
    if args.close:
        return close_running()
    if paths.frozen() or os.environ.get("BOKIN_LOG_FILE"):
        log_to_file()
    if args.selftest:
        from bokin_suno import selftest
        return selftest.run()
    return serve(updated=args.updated)


def entry() -> None:
    code = 1
    try:
        code = main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
    except BaseException:  # noqa: BLE001 - the log is the only place an installed app can say it
        import traceback
        traceback.print_exc()
    finally:
        try:
            sys.stdout.flush()
        except (OSError, ValueError, AttributeError):
            pass
    os._exit(code)  # the mastering worker thread may still be running
