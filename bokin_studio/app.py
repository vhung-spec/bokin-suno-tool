"""Bokin Suno Studio's local server: one page with four tabs, and its API.

- Tài khoản / Tải nhạc: the Suno downloader (suno_tasks.py runs suno/bokin_suno.py), the songs downloaded into a
  folder with their lyrics (library.py).
- Đổi lời: Lời Đồng Âm (loi-dong-am/, unchanged) in a frame; the page puts a song's lyrics into it.
- Master: Bokin Suno Master's own page (bokin_suno/static/index.html, unchanged) in a frame, over the same API
  paths as in Bokin Suno Master (/api/jobs, /api/files, /api/info...), served here from bokin_suno.app.Jobs; a
  downloaded song can be sent to it.

It listens on 127.0.0.1 only. Every API call must carry the per-launch token embedded in the page (desktop.py also
keeps it in the user's data folder for the installer), so other websites open in the same browser cannot use it,
and the Host header is checked against DNS rebinding. Lời Đồng Âm's files are static and hold nothing of the user:
they are served without the token. Until a Bokin License key for this computer is activated (licensing.py),
everything but the page, its activation screen, updates and quitting is refused.
"""

import json
import os
import re
import secrets
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

import bokin_license
from bokin_studio import library, licensing, paths
from bokin_studio.suno_tasks import Busy, SunoTasks, chrome_path
from bokin_suno.app import Jobs
from bokin_suno.audio_io import AUDIO_EXTENSIONS, FORMATS
from bokin_suno.master import PRESETS, Settings, preset

STATIC = Path(__file__).resolve().parent / "static"
MASTER_PAGE = Path(__file__).resolve().parent.parent / "bokin_suno" / "static" / "index.html"
LYRICS_FILES = {"index.html": "text/html; charset=utf-8", "engine.js": "text/javascript; charset=utf-8",
                "hyphen-en-us.js": "text/javascript; charset=utf-8"}
NO_TOKEN = {"/", "/favicon.ico", "/logo.svg", "/api/ping"} | {f"/loi-dong-am/{name}" for name in LYRICS_FILES}
FREE_PATHS = NO_TOKEN | {"/api/info", "/api/license", "/api/update", "/api/update/check", "/api/update/install",
                         "/api/quit", "/api/shutdown"}
ACCOUNT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}")  # as suno/bokin_suno.py
SONG_LINK = re.compile(r"https?://[A-Za-z0-9.:-]+/song/[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
# the Master frame: Bokin Suno Master's page without its own header (title, version, update, quit: the Studio's)
MASTER_STYLE = "<style>header { display: none !important; } main { padding-top: 12px !important; }</style>"
# the Đổi lời frame: Lời Đồng Âm (its file unchanged: it is also published on its own) in the app's look, the colours,
# type and corners of the app's other tabs; its title and lede are the tab's own, its Public Domain reminder stays.
# No web fonts: the app's system font, and nothing fetched from the Internet.
LYRICS_STYLE = """<style>
:root:root:root {
  --paper: #f6f5f2; --sheet: #ffffff; --ink: #1d1d1f; --muted: #6b6b70; --rule: #e3e1dc; --staff: #e3e1dc;
  --accent: #3b5bdb; --accent-ink: #ffffff; --warn: #b26a00; --warn-bg: #fdf3e1;
  --shadow: none;
  --f-display: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --f-ui: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --f-lyric: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:root:root {
    --paper: #141416; --sheet: #1d1d21; --ink: #ececf0; --muted: #9a9aa3; --rule: #2e2e35; --staff: #2e2e35;
    --accent: #7b93ff; --accent-ink: #0d0d10; --warn: #ffc078; --warn-bg: rgba(255, 192, 120, .1);
  }
}
body { font: 15px/1.5 var(--f-ui) !important; }
.wrap { max-width: 1000px !important; padding-block: 16px 60px !important; gap: 16px !important; }
.masthead h1, .masthead .lede, .staff { display: none !important; }
.notice { font-size: 14px !important; padding: 10px 12px !important; }
.sheet, .custom, .pop { border-radius: 12px !important; box-shadow: none !important; }
.sheet-head h2, .guide h2, .custom summary { font-size: 16px !important; font-weight: 600 !important; }
.btn, .sheet-head select, .opt .pick, .icon-btn, .own input, .custom textarea { border-radius: 8px !important; }
.seg label:first-of-type { border-radius: 8px 0 0 8px !important; }
.seg label:last-of-type { border-radius: 0 8px 8px 0 !important; }
.lyrics, textarea#src { font-size: 15px !important; line-height: 1.75 !important; }
</style>"""


def master_page_path() -> Path:
    if MASTER_PAGE.is_file():
        return MASTER_PAGE
    return paths.root_dir() / "bokin_suno" / "static" / "index.html"  # (the installed app's bundle)


def lyrics_dir() -> Path:
    return paths.root_dir() / "loi-dong-am"


class Shared:
    """What the request handlers and the desktop launcher share."""

    def __init__(self, desktop: bool, suno: SunoTasks, jobs: Jobs):
        self.desktop, self.suno, self.jobs = desktop, suno, jobs
        self.server = None    # the uvicorn server, to stop it
        self.updater = None   # updater.AutoUpdate of an installed app
        self.quit = threading.Event()
        self.relaunch = False  # quit to install the downloaded update, then start again
        self.seen = time.time()  # the page's last call: the installed app quits a while after it stops

    def busy(self) -> bool:
        """A Suno task runs, or a song is being mastered (or waits its turn): quitting now would lose it."""
        return self.suno.busy() or self.jobs.busy()

    def stop(self) -> None:
        self.quit.set()
        self.suno.shutdown()
        if self.server is not None:
            self.server.should_exit = True

    def update_state(self) -> dict:
        state = dict(self.updater.state) if self.updater else {
            "current": paths.version(), "available": None, "ready": False, "error": None, "reason": None,
            "checked": None, "downloading": None}
        return {**state, "auto": self.updater is not None}


def read_settings() -> dict:
    try:
        value = json.loads(paths.settings_path().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_settings(value: dict) -> None:
    path = paths.settings_path()
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def open_in_explorer(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # noqa: S606 - a folder of this user's own
    else:
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# Windows' folder dialog, from a PowerShell of its own. Windows keeps a program in the background from putting its
# window in front, so the dialog belongs to a tiny form that stays on top of every window (TopMost, shown off screen):
# it opens above the app instead of behind it. The chosen folder comes back in a UTF-8 file (a folder name may have
# Vietnamese letters, which a console without a window would mangle); the texts go in as environment variables.
PICK_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$o = New-Object System.Windows.Forms.Form
$o.TopMost = $true; $o.ShowInTaskbar = $false; $o.StartPosition = 'Manual'; $o.FormBorderStyle = 'None'
$o.Location = New-Object System.Drawing.Point(-32000, -32000); $o.Size = New-Object System.Drawing.Size(1, 1)
$o.Show(); $o.Activate()
$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = $env:BOKIN_PICK_TEXT
$d.ShowNewFolderButton = $true
if ($env:BOKIN_PICK_START) { $d.SelectedPath = $env:BOKIN_PICK_START }
$r = $d.ShowDialog($o)
$o.Close()
if ($r -eq [System.Windows.Forms.DialogResult]::OK) {
  [IO.File]::WriteAllText($env:BOKIN_PICK_OUT, $d.SelectedPath, (New-Object System.Text.UTF8Encoding $false))
}
"""


class PickError(Exception):
    pass


def can_pick() -> bool:
    """Is there a folder dialog to show (Windows)?"""
    return os.name == "nt"


def pick_folder(start: str = "") -> str | None:
    """Windows' own folder dialog, on top of the app's window; "" if cancelled, None where there is none. PickError
    (the reason) if it could not be shown."""
    if os.name != "nt":
        return None
    path = Path(start) if start else None
    while path is not None and not path.is_dir():  # (a folder not made yet: start from the nearest one there is)
        path = path.parent if path.parent != path else None
    with tempfile.TemporaryDirectory(prefix="bokin-pick-") as tmp:
        out = Path(tmp) / "folder.txt"
        env = dict(os.environ, BOKIN_PICK_START=str(path or ""), BOKIN_PICK_OUT=str(out),
                   BOKIN_PICK_TEXT="Chọn thư mục lưu nhạc")
        try:
            r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-ExecutionPolicy", "Bypass",
                                "-Command", PICK_SCRIPT], capture_output=True, env=env, timeout=3600,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise PickError(f"Không mở được hộp chọn thư mục: {e}") from e
        if r.returncode != 0:
            why = r.stderr.decode("utf-8", "replace").strip().splitlines()
            print(f"pick folder: {r.returncode} {why}", flush=True)
            raise PickError("Không mở được hộp chọn thư mục" + (f": {why[0][:200]}" if why else ""))
        return out.read_text(encoding="utf-8").strip() if out.exists() else ""


def _folder(value) -> Path:
    if not isinstance(value, str) or not value.strip():
        return paths.music_dir()
    if len(value) > 500 or "\x00" in value:
        raise HTTPException(400, "Đường dẫn thư mục không hợp lệ")
    path = Path(value.strip().strip('"')).expanduser()
    if not path.is_absolute():
        raise HTTPException(400, "Hãy ghi đường dẫn đầy đủ của thư mục, ví dụ D:\\Nhac\\Suno")
    return path


def _account(value) -> str:
    if not isinstance(value, str) or not ACCOUNT.fullmatch(value):
        raise HTTPException(400, "Tên tài khoản chỉ gồm chữ không dấu, số, - và _ (tối đa 40), ví dụ suno1")
    return value


def _links(value) -> list:
    if isinstance(value, str):
        value = value.split()
    if not isinstance(value, list):
        raise HTTPException(400, "Hãy dán link workspace của Suno")
    links = [v.strip() for v in value if isinstance(v, str) and v.strip()]
    if not links:
        raise HTTPException(400, "Hãy dán link workspace của Suno")
    if len(links) > 20 or any(len(v) > 2000 or v.startswith("-") for v in links):
        raise HTTPException(400, "Link không hợp lệ (tối đa 20 link, mỗi link một dòng)")
    return links


def create_app(token: str, port: int = paths.PORTS[0], extra_hosts: tuple = (), desktop: bool = False,
               suno_data: Path | None = None, master_out: Path | None = None) -> FastAPI:
    app = FastAPI(title="Bokin Suno Studio", docs_url=None, redoc_url=None, openapi_url=None)
    jobs = Jobs(Path(master_out or paths.master_dir()).resolve())
    suno = SunoTasks(suno_data or paths.suno_data_dir())
    shared = Shared(desktop, suno, jobs)
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}", *extra_hosts}

    @app.middleware("http")
    async def guard(request: Request, call_next):
        path = request.url.path
        if request.headers.get("host", "") not in allowed_hosts:
            return JSONResponse({"detail": "bad host"}, status_code=403)
        if path == "/favicon.ico":
            return Response(status_code=204)
        if path not in NO_TOKEN:
            supplied = request.headers.get("x-bokin-token") or request.query_params.get("t")
            if not supplied or not secrets.compare_digest(supplied.encode("utf-8"), token.encode("utf-8")):
                return JSONResponse({"detail": "missing or wrong token"}, status_code=403)
            shared.seen = time.time()
            if path not in FREE_PATHS and not licensing.licensed():
                return JSONResponse({"detail": "Bokin Suno Studio chưa được kích hoạt trên máy này.",
                                     "license": True}, status_code=403)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    # ---- pages ----

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (STATIC / "index.html").read_text(encoding="utf-8").replace("__BOKIN_TOKEN__", token)

    @app.get("/logo.svg")
    def logo():
        """The app's icon (the "Ss" tile of the Bokin family): the window's icon and the page's header."""
        return Response((STATIC / "logo.svg").read_bytes(), media_type="image/svg+xml",
                        headers={"Cache-Control": "max-age=86400"})

    @app.get("/master", response_class=HTMLResponse)
    def master_frame():
        html = master_page_path().read_text(encoding="utf-8").replace("__BOKIN_TOKEN__", token)
        return html.replace("</head>", MASTER_STYLE + "</head>", 1)

    @app.get("/loi-dong-am/{name}")
    def lyrics_file(name: str):
        if name not in LYRICS_FILES:
            raise HTTPException(404, "not found")
        if name == "index.html":  # (in the app's look, without web fonts)
            html = (lyrics_dir() / name).read_text(encoding="utf-8")
            html = re.sub(r'<link rel="(preconnect|stylesheet)" href="https://fonts\.[^"]*"[^>]*>\n?', "", html)
            return HTMLResponse(html.replace("</head>", LYRICS_STYLE + "\n</head>", 1))
        return Response((lyrics_dir() / name).read_bytes(), media_type=LYRICS_FILES[name])

    # ---- the app ----

    @app.get("/api/ping")
    def ping():
        return {"app": paths.APP_ID, "version": paths.version(), "owner": paths.owner()}

    @app.get("/api/info")
    def info():
        return {"version": paths.version(), "out_dir": str(jobs.dir), "formats": list(FORMATS),
                "extensions": sorted(AUDIO_EXTENSIONS), "desktop": desktop,
                "presets": {name: preset(name).to_dict() for name in PRESETS},
                "music_dir": str(paths.music_dir()), "pick_folder": desktop and can_pick()}

    @app.get("/api/license")
    def license_view():
        return licensing.view()

    @app.post("/api/license")
    def license_activate(body: dict):
        try:
            return licensing.activate(body.get("key"))
        except bokin_license.LicenseError as err:
            raise HTTPException(400, str(err)) from err

    @app.get("/api/update")
    def update_state():
        return shared.update_state()

    @app.post("/api/update/check")
    def update_check():
        started = bool(shared.updater and shared.updater.check_soon())
        return {**shared.update_state(), "started": started}

    @app.post("/api/update/install")
    def update_install():
        up = shared.updater
        if not up or not up.state.get("ready") or not up.installer or not os.path.exists(up.installer):
            raise HTTPException(400, "Chưa có bản cập nhật sẵn sàng.")
        if shared.busy():
            raise HTTPException(400, "App đang tải nhạc hoặc master bài hát. Cập nhật sau khi xong.")
        shared.relaunch = True
        shared.stop()
        return {"ok": True}

    @app.post("/api/quit")
    def quit_app():
        """The installer (desktop --close) asks before replacing the files."""
        if shared.busy():
            return {"busy": True}
        shared.relaunch = False
        shared.stop()
        return {"ok": True}

    @app.post("/api/shutdown")
    def shutdown():
        """The page's "Tắt app" button: quits even while busy (it asked first)."""
        shared.relaunch = False
        shared.stop()
        return {"stopping": True}

    @app.post("/api/open")
    def open_folder(body: dict):
        """A master job's folder, a music folder, or (Bokin Suno Master's page: no folder) the Master folder."""
        if not desktop:
            raise HTTPException(400, "Chỉ mở được thư mục ở app cài trên máy.")
        if body.get("job"):
            target = jobs.get(body["job"]).dir
        elif "folder" in body:  # (empty: the default music folder, as everywhere)
            target = _folder(body["folder"])
            if not target.is_dir():
                raise HTTPException(400, "Thư mục chưa có (chưa tải bài nào vào đó)")
        else:
            target = jobs.dir
        open_in_explorer(target)
        return {"ok": True}

    @app.get("/api/settings")
    def settings_get():
        return read_settings()

    @app.post("/api/settings")
    def settings_set(body: dict):
        keep = {}
        for key, kind in (("account", str), ("links", str), ("folder", str), ("format", str), ("preset", str)):
            if isinstance(body.get(key), kind) and len(body[key]) <= 20_000:
                keep[key] = body[key]
        if isinstance(body.get("stems"), bool):
            keep["stems"] = body["stems"]
        write_settings({**read_settings(), **keep})
        return read_settings()

    @app.post("/api/pick-folder")
    def pick(body: dict):
        if not desktop:
            raise HTTPException(400, "Hãy gõ đường dẫn thư mục.")
        try:
            found = pick_folder(str(body.get("start") or ""))
        except PickError as err:
            raise HTTPException(400, f"{err}. Hãy gõ (hoặc dán) đường dẫn thư mục vào ô.") from err
        if found is None:
            raise HTTPException(400, "Hãy gõ đường dẫn thư mục.")
        return {"folder": found}

    # ---- Suno ----

    def run(kind, args, label, body=None):
        try:
            task = suno.start(kind, args, label, headless=bool((body or {}).get("headless")),
                              chrome=os.environ.get("BOKIN_STUDIO_CHROME"))
        except Busy as err:
            raise HTTPException(409, str(err)) from err
        return task.to_dict()

    @app.get("/api/suno")
    def suno_state(since: int = 0, songs: int = 1):
        """songs=0: the page already shows the listed songs of this task (they are not sent again)."""
        task = suno.task
        return {"accounts": suno.accounts(), "chrome": bool(os.environ.get("BOKIN_STUDIO_CHROME") or chrome_path()),
                "task": task.to_dict(since, songs=bool(songs)) if task else None}

    @app.post("/api/suno/login")
    def suno_login(body: dict):
        name = _account(body.get("account"))
        return run("login", [name], f"Đăng nhập Suno: {name}")

    @app.post("/api/suno/check")
    def suno_check(body: dict):
        args = [_account(body["account"])] if body.get("account") else []
        return run("check", args, "Kiểm tra đăng nhập", body)

    @app.post("/api/suno/remove")
    def suno_remove(body: dict):
        name = _account(body.get("account"))
        return run("remove", [name], f"Xoá tài khoản {name}")

    @app.post("/api/suno/list")
    def suno_list(body: dict):
        name = _account(body.get("account"))
        return run("list", [name] + _links(body.get("links")), "Xem danh sách bài", body)

    @app.post("/api/suno/download")
    def suno_download(body: dict):
        name = _account(body.get("account"))
        args = [name] + _links(body.get("links")) + ["--out", str(_folder(body.get("folder")))]
        fmt = body.get("format") or "wav"
        if fmt not in ("wav", "mp3"):
            raise HTTPException(400, "Định dạng phải là WAV hoặc MP3")
        args += ["--format", fmt]
        if body.get("limit") not in (None, "", 0):
            try:
                limit = int(body["limit"])
            except (TypeError, ValueError):
                limit = 0
            if limit < 1:
                raise HTTPException(400, "Số bài tối đa phải từ 1 trở lên")
            args += ["--limit", str(limit)]
        if body.get("full"):
            args.append("--full")
        label = f"Tải nhạc ({fmt.upper()})"
        if body.get("stems"):  # WAV, MP3 and MIDI, Follow tempo changes; Extract when not made yet (the owner's choice)
            args.append("--stems")
            label = f"Tải nhạc ({fmt.upper()}) và Stems & MIDI"
        return run("download", args, label, body)

    @app.post("/api/suno/stems")
    def suno_stems(body: dict):
        """The Stems & MIDI of one downloaded song (the song table's Stems button)."""
        name = _account(body.get("account"))
        folder = _folder(body.get("folder"))
        row = library_call(library.song_row, folder, body.get("file"))
        link = row.get("link", "")
        if not SONG_LINK.match(link):  # (one song's own link: never a workspace's, whatever the list says)
            raise HTTPException(400, "Bài này không có link bài hát Suno trong danh-sach.csv")
        return run("stems", [name, link, "--out", str(folder)], f"Tải Stems & MIDI: {row['title']}", body)

    @app.post("/api/suno/stop")
    def suno_stop():
        return {"stopping": suno.stop()}

    # ---- the downloaded songs ----

    def library_call(fn, *args):
        try:
            return fn(*args)
        except library.LibraryError as err:
            raise HTTPException(400, str(err)) from err

    @app.get("/api/library")
    def library_songs(folder: str = ""):
        target = _folder(folder)
        return {"folder": str(target), "songs": library_call(library.songs, target)}

    @app.get("/api/library/lyrics")
    def library_lyrics(folder: str, file: str):
        return {"lyrics": library_call(library.lyrics, _folder(folder), file)}

    @app.get("/api/library/audio")
    def library_audio(folder: str, file: str):
        path = library_call(library.song_file, _folder(folder), file)
        return FileResponse(path, media_type="audio/wav" if path.suffix.lower() == ".wav" else "audio/mpeg")

    @app.post("/api/library/open-stems")
    def library_open_stems(body: dict):
        if not desktop:
            raise HTTPException(400, "Chỉ mở được thư mục ở app cài trên máy.")
        open_in_explorer(library_call(library.stems_folder, _folder(body.get("folder")), body.get("file")))
        return {"ok": True}

    @app.post("/api/library/master")
    def library_master(body: dict):
        path = library_call(library.song_file, _folder(body.get("folder")), body.get("file"))
        name = body.get("preset") or "streaming"
        if name not in PRESETS:
            raise HTTPException(400, "Không có kiểu master này")
        with open(path, "rb") as f:
            job = jobs.add(SimpleNamespace(filename=path.name, file=f), None, preset(name), name)
        return job.to_dict()

    # ---- Bokin Suno Master's API (its page, in the Master tab) ----

    @app.post("/api/jobs")
    def add_job(song: UploadFile = File(...), reference: UploadFile | None = File(None),
                settings: str = Form("{}"), preset_name: str = Form("", alias="preset")):
        try:
            parsed = Settings.from_dict(json.loads(settings))
            parsed.check()
        except (ValueError, json.JSONDecodeError) as err:
            raise HTTPException(400, f"Cài đặt không hợp lệ: {err}") from err
        for upload in (song, reference):
            if upload is not None and Path(upload.filename or "").suffix.lower() not in AUDIO_EXTENSIONS:
                raise HTTPException(400, f"Không đọc được loại file này: {upload.filename}")
        return jobs.add(song, reference, parsed, preset_name if preset_name in PRESETS else None).to_dict()

    @app.get("/api/jobs")
    def list_jobs():
        return jobs.list()

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        return jobs.get(job_id).to_dict()

    @app.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str):
        jobs.delete(job_id)
        return {"deleted": job_id}

    @app.get("/api/peaks/{job_id}/{name}")
    def get_peaks(job_id: str, name: str):
        """A result file's waveform (the compare player)."""
        job = jobs.get(job_id)
        if name not in job.files.values():
            raise HTTPException(404, "Không có file này")
        try:
            return jobs.peaks(job, name)
        except Exception as err:  # noqa: BLE001 - the player then shows no waveform
            raise HTTPException(500, f"Không đọc được {name}: {err}") from err

    @app.get("/api/files/{job_id}/{name}")
    def get_file(job_id: str, name: str, download: bool = False):
        job = jobs.get(job_id)
        if name not in job.files.values() or not (job.dir / name).is_file():  # (moved or deleted by hand)
            raise HTTPException(404, "Không có file này")
        return FileResponse(job.dir / name, filename=name if download else None,
                            content_disposition_type="attachment" if download else "inline")

    app.state.bokin = shared
    app.state.jobs = jobs
    app.state.suno = suno
    return app
