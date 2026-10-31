"""Bokin Suno Master's local server: the page and its API over master_file().

It listens on 127.0.0.1 only. Every API call must carry the per-launch token
that is embedded in the page (desktop.py also keeps it in the user's data
folder for the installer), so other websites open in the same browser cannot
use it, and the Host header is checked against DNS rebinding. Until a Bokin
License key for this computer is activated (licensing.py), everything but the
page, its activation screen and the update and quit calls is refused.

Each song becomes a job folder in the output folder: the uploaded song (and
reference), the results and the report. One job runs at a time; the list
of past jobs is read back from the folders, so it survives a restart.

desktop.py starts it (the installed app, `bokin-suno app`).
"""

import json
import os
import queue
import re
import secrets
import shutil
import subprocess
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

import bokin_license
from bokin_suno import audio_io, licensing, paths
from bokin_suno.audio_io import AUDIO_EXTENSIONS, FORMATS
from bokin_suno.master import PRESETS, Settings, master_file, preset, style_of

DEFAULT_PORT = paths.PORTS[0]
# Answer without the per-launch token: the page (it carries the token) and the "who is there" ping.
NO_TOKEN = {"/", "/favicon.ico", "/api/ping"}
# Answer before the app is activated: the page and its activation screen, the version and
# presets, updates, quitting. Everything else is refused (the page then shows the activation screen).
FREE_PATHS = NO_TOKEN | {"/api/info", "/api/license", "/api/update", "/api/update/check",
                         "/api/update/install", "/api/quit", "/api/shutdown"}
STATIC = Path(__file__).resolve().parent / "static"
JOB_ID = r"^[0-9]{8}-[0-9]{6}-[A-Za-z0-9_-]{1,40}$"
SETTINGS_FILE = "settings.json"
ERROR_FILE = "error.txt"
PEAK_COLUMNS = 1200  # a waveform's columns (the page's compare player)
PEAKS_FILE = "peaks.json"  # the waveforms of a job's files, worked out once


def _safe_name(name: str) -> str:
    """A file name without folders or odd characters (letters with accents stay)."""
    name = Path(name.replace("\\", "/")).name
    stem, suffix = Path(name).stem, Path(name).suffix.lower()
    stem = re.sub(r"[^\w\- ]+", "_", stem).strip(" ._") or "song"
    return f"{stem[:80]}{suffix}"


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", Path(name).stem).strip("-")[:40] or "song"


@dataclass
class Job:
    id: str
    dir: Path
    song: str
    reference: str | None = None
    state: str = "queued"  # queued, running, done, failed, interrupted
    stage: str = ""
    fraction: float = 0.0
    error: str | None = None
    report: dict | None = None
    files: dict = field(default_factory=dict)
    style: dict | None = None  # the kiểu master (master.style_of)
    peaks: dict = field(default_factory=dict)  # file name -> its waveform (Jobs.peaks)

    def to_dict(self) -> dict:
        return {"id": self.id, "song": self.song, "reference": self.reference,
                "state": self.state, "stage": self.stage, "fraction": round(self.fraction, 3),
                "error": self.error, "report": self.report, "files": self.files, "style": self.style}


class Jobs:
    def __init__(self, out_dir: Path):
        self.dir = out_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.queue: queue.Queue[Job] = queue.Queue()
        self.peaks_lock = threading.Lock()  # (one waveform worked out at a time: they read whole files)
        self._load()
        threading.Thread(target=self._worker, daemon=True).start()

    def _load(self) -> None:
        """Past jobs, from their folders."""
        for d in sorted(p for p in self.dir.iterdir() if p.is_dir() and re.match(JOB_ID, p.name)):
            meta = d / SETTINGS_FILE
            if not meta.is_file():
                continue
            info = json.loads(meta.read_text(encoding="utf-8"))
            job = Job(d.name, d, info["song"], info.get("reference"))
            job.style = info.get("style")
            if job.style is None:  # (a song mastered before the kiểu master was kept: told by its settings)
                try:
                    job.style = style_of(Settings.from_dict(info["settings"]))
                except (KeyError, TypeError, ValueError):
                    pass
            reports = list(d.glob("*_report.json"))
            if reports:
                job.report = json.loads(reports[0].read_text(encoding="utf-8"))
                job.state = "done"
                job.files = self._files(job)
            elif (d / ERROR_FILE).is_file():  # the message, then the traceback
                job.state = "failed"
                job.error = (d / ERROR_FILE).read_text(encoding="utf-8").split("\n\n")[0]
            else:
                job.state = "interrupted"  # the app closed while it ran
            self.jobs[job.id] = job

    @staticmethod
    def _files(job: Job) -> dict:
        r = job.report or {}
        files = {"source": job.song, "master": r.get("output_file"), "removed": r.get("removed_file")}
        return {k: v for k, v in files.items() if v and (job.dir / v).is_file()}

    def add(self, song: UploadFile, reference: UploadFile | None, settings: Settings,
            preset_name: str | None = None) -> Job:
        """preset_name: the kiểu master chosen (the settings may have been moved off it)."""
        song_name = _safe_name(song.filename or "song.wav")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        with self.lock:
            job_id, n = f"{stamp}-{_slug(song_name)}", 1
            while job_id in self.jobs or (self.dir / job_id).exists():
                n += 1
                job_id = f"{stamp}-{_slug(song_name)[:36]}-{n}"
            d = self.dir / job_id
            d.mkdir(parents=True)
            job = Job(job_id, d, song_name, style=style_of(settings, preset_name))
            self.jobs[job_id] = job
        with open(d / song_name, "wb") as f:
            shutil.copyfileobj(song.file, f)
        if reference is not None:
            ref_name = "ref_" + _safe_name(reference.filename or "reference.wav")
            with open(d / ref_name, "wb") as f:
                shutil.copyfileobj(reference.file, f)
            job.reference = ref_name
        (d / SETTINGS_FILE).write_text(json.dumps(
            {"song": song_name, "reference": job.reference, "settings": settings.to_dict(), "style": job.style},
            indent=2, ensure_ascii=False), encoding="utf-8")
        self.queue.put(job)
        return job

    def _worker(self) -> None:
        while True:
            job = self.queue.get()
            if job.id not in self.jobs:
                continue  # deleted while queued
            job.state = "running"

            def progress(stage: str, fraction: float, job=job):
                job.stage, job.fraction = stage, fraction

            try:
                info = json.loads((job.dir / SETTINGS_FILE).read_text(encoding="utf-8"))
                result = master_file(job.dir / job.song, job.dir,
                                     Settings.from_dict(info["settings"]),
                                     job.dir / job.reference if job.reference else None,
                                     progress=progress, label=(info.get("style") or {}).get("label"))
                job.report = result.report
                job.files = self._files(job)
                for name in job.files.values():  # (the page's waveforms, ready when it asks)
                    try:
                        self.peaks(job, name)
                    except Exception:  # noqa: BLE001 - worked out again when asked
                        pass
                job.state = "done"
            except Exception as err:
                job.error = str(err) or type(err).__name__
                (job.dir / ERROR_FILE).write_text(job.error + "\n\n" + traceback.format_exc(),
                                                  encoding="utf-8")
                job.state = "failed"

    def peaks(self, job: Job, name: str, columns: int = PEAK_COLUMNS) -> dict:
        """A file's waveform for the page: {"seconds", "peaks": [low, high] per column, both channels}. Read block by
        block, one file at a time, then kept in the job's folder (peaks.json)."""
        with self.peaks_lock:
            if not job.peaks:
                try:
                    job.peaks = json.loads((job.dir / PEAKS_FILE).read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    job.peaks = {}
            if name not in job.peaks:
                job.peaks[name] = _peaks(job.dir / name, columns)
                try:
                    (job.dir / PEAKS_FILE).write_text(json.dumps(job.peaks), encoding="utf-8")
                except OSError:
                    pass
            return job.peaks[name]

    def list(self) -> list[dict]:
        return [j.to_dict() for j in sorted(self.jobs.values(), key=lambda j: j.id, reverse=True)]

    def busy(self) -> bool:
        """A song is being mastered or waits its turn: quitting now would lose it."""
        return any(j.state in ("queued", "running") for j in list(self.jobs.values()))

    def get(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Không có việc này")
        return job

    def delete(self, job_id: str) -> None:
        """The job's folder, its audio files first: one still open (Windows: a player still reading it) leaves the
        job listed, to be deleted again, instead of a folder nothing lists any more."""
        job = self.get(job_id)
        if job.state == "running":
            raise HTTPException(409, "Đang xử lý, chờ xong rồi xoá")
        names = [job.song, job.reference, *job.files.values()]
        for path in [job.dir / n for n in dict.fromkeys(n for n in names if n)]:
            for attempt in range(10):
                try:
                    path.unlink(missing_ok=True)
                    break
                except PermissionError:
                    if attempt == 9:
                        raise HTTPException(409, f"Không xoá được {path.name}: file đang được mở. Chờ vài giây rồi "
                                                 "bấm Xoá lại") from None
                    time.sleep(0.3)
        self.jobs.pop(job_id, None)  # (pressed twice: the second finds it gone)
        shutil.rmtree(job.dir, ignore_errors=True)


def _peaks(path: Path, columns: int) -> dict:
    """The low and high of each of `columns` stretches of a file (both channels), read block by block."""
    def fill(blocks, n):
        cols = max(1, min(columns, n))
        edges = np.linspace(0, n, cols + 1).astype(np.int64)
        lo, hi = np.full(cols, np.inf, np.float32), np.full(cols, -np.inf, np.float32)
        pos = 0
        for block in blocks:
            m = min(len(block), n - pos)
            if m <= 0:
                break
            bl, bh = block[:m].min(axis=1), block[:m].max(axis=1)
            c0 = int(np.searchsorted(edges, pos, side="right")) - 1
            c1 = min(cols - 1, int(np.searchsorted(edges, pos + m - 1, side="right")) - 1)
            starts = np.maximum(edges[c0:c1 + 1], pos) - pos
            lo[c0:c1 + 1] = np.minimum(lo[c0:c1 + 1], np.minimum.reduceat(bl, starts))
            hi[c0:c1 + 1] = np.maximum(hi[c0:c1 + 1], np.maximum.reduceat(bh, starts))
            pos += m
        both = np.column_stack([np.where(np.isfinite(lo), lo, 0), np.where(np.isfinite(hi), hi, 0)])
        return np.round(both.ravel().astype(np.float64), 4).tolist()

    try:
        info = sf.info(str(path))
        if info.frames <= 0:
            raise RuntimeError("no frames")
        peaks = fill(sf.blocks(str(path), blocksize=1 << 18, dtype="float32", always_2d=True), info.frames)
        return {"seconds": round(info.frames / info.samplerate, 3), "peaks": peaks}
    except RuntimeError:  # a format libsndfile cannot read (m4a...): the whole file, through ffmpeg
        x, sr = audio_io.load(path)
        return {"seconds": round(len(x) / sr, 3), "peaks": fill([x.astype(np.float32)], len(x))}


class Shared:
    """What the request handlers and the desktop launcher share."""

    def __init__(self, desktop: bool):
        self.desktop = desktop
        self.server = None    # the uvicorn server, to stop it
        self.updater = None   # updater.AutoUpdate of an installed app
        self.quit = threading.Event()
        self.relaunch = False  # quit to install the downloaded update, then start again
        self.seen = time.time()  # the page's last call: the installed app quits a while after it stops

    def stop(self) -> None:
        self.quit.set()
        if self.server is not None:
            self.server.should_exit = True

    def update_state(self) -> dict:
        state = dict(self.updater.state) if self.updater else {
            "current": paths.version(), "available": None, "ready": False, "error": None, "reason": None,
            "checked": None, "downloading": None}
        return {**state, "auto": self.updater is not None}


def open_in_explorer(path: Path) -> None:
    if os.name == "nt":
        os.startfile(path)  # noqa: S606 - our own output folder
    else:
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def create_app(token: str, out_dir: Path, port: int = DEFAULT_PORT,
               extra_hosts: tuple[str, ...] = (), desktop: bool = False) -> FastAPI:
    app = FastAPI(title="Bokin Suno Master", docs_url=None, redoc_url=None, openapi_url=None)
    jobs = Jobs(Path(out_dir).resolve())
    shared = Shared(desktop)
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
            if not supplied or not secrets.compare_digest(supplied, token):
                return JSONResponse({"detail": "missing or wrong token"}, status_code=403)
            shared.seen = time.time()
            if path not in FREE_PATHS and not licensing.licensed():
                return JSONResponse({"detail": "Bokin Suno Master chưa được kích hoạt trên máy này.",
                                     "license": True}, status_code=403)
        return await call_next(request)

    @app.get("/", response_class=HTMLResponse)
    def index():
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        return html.replace("__BOKIN_TOKEN__", token)

    @app.get("/api/ping")
    def ping():
        return {"app": paths.APP_ID, "version": paths.version(), "owner": paths.owner()}

    @app.get("/api/info")
    def info():
        return {"version": paths.version(), "out_dir": str(jobs.dir), "formats": list(FORMATS),
                "extensions": sorted(AUDIO_EXTENSIONS), "desktop": desktop,
                "presets": {name: preset(name).to_dict() for name in PRESETS}}

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
        if jobs.busy():
            raise HTTPException(400, "App đang master bài hát. Cập nhật sau khi xong.")
        shared.relaunch = True
        shared.stop()
        return {"ok": True}

    @app.post("/api/quit")
    def quit_app():
        """The installer (desktop --close) asks before replacing the files."""
        if jobs.busy():
            return {"busy": True}
        shared.relaunch = False
        shared.stop()
        return {"ok": True}

    @app.post("/api/shutdown")
    def shutdown():
        """The page's "Tắt app" button: quits even while a song is being mastered (it asked first)."""
        shared.relaunch = False
        shared.stop()
        return {"stopping": True}

    @app.post("/api/open")
    def open_folder(body: dict):
        if not desktop:
            raise HTTPException(400, "Chỉ mở được thư mục ở app cài trên máy.")
        job_id = body.get("job")
        target = jobs.get(job_id).dir if job_id else jobs.dir
        open_in_explorer(target)
        return {"ok": True}

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
    return app
