"""Bokin Suno Master web app: a local page over master_file().

    bokin-suno app --open        start it and open the browser

It listens on 127.0.0.1 only. Every API call must carry the per-launch token
that is embedded in the page, so other websites open in the same browser
cannot use it, and the Host header is checked against DNS rebinding.

Each song becomes a job folder in the output folder: the uploaded song (and
reference), the results and the report. One job runs at a time; the list
of past jobs is read back from the folders, so it survives a restart.
"""

import json
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

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response

from bokin_suno import __version__
from bokin_suno.audio_io import AUDIO_EXTENSIONS, FORMATS
from bokin_suno.master import PRESETS, Settings, master_file, preset

DEFAULT_PORT = 8766  # Bokin Music uses 8765
STATIC = Path(__file__).resolve().parent / "static"
JOB_ID = r"^[0-9]{8}-[0-9]{6}-[A-Za-z0-9_-]{1,40}$"
SETTINGS_FILE = "settings.json"
ERROR_FILE = "error.txt"


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

    def to_dict(self) -> dict:
        return {"id": self.id, "song": self.song, "reference": self.reference,
                "state": self.state, "stage": self.stage, "fraction": round(self.fraction, 3),
                "error": self.error, "report": self.report, "files": self.files}


class Jobs:
    def __init__(self, out_dir: Path):
        self.dir = out_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.queue: queue.Queue[Job] = queue.Queue()
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

    def add(self, song: UploadFile, reference: UploadFile | None, settings: Settings) -> Job:
        song_name = _safe_name(song.filename or "song.wav")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        with self.lock:
            job_id, n = f"{stamp}-{_slug(song_name)}", 1
            while job_id in self.jobs or (self.dir / job_id).exists():
                n += 1
                job_id = f"{stamp}-{_slug(song_name)[:36]}-{n}"
            d = self.dir / job_id
            d.mkdir(parents=True)
            job = Job(job_id, d, song_name)
            self.jobs[job_id] = job
        with open(d / song_name, "wb") as f:
            shutil.copyfileobj(song.file, f)
        if reference is not None:
            ref_name = "ref_" + _safe_name(reference.filename or "reference.wav")
            with open(d / ref_name, "wb") as f:
                shutil.copyfileobj(reference.file, f)
            job.reference = ref_name
        (d / SETTINGS_FILE).write_text(json.dumps(
            {"song": song_name, "reference": job.reference, "settings": settings.to_dict()},
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
                                     progress=progress)
                job.report = result.report
                job.files = self._files(job)
                job.state = "done"
            except Exception as err:
                job.error = str(err) or type(err).__name__
                (job.dir / ERROR_FILE).write_text(job.error + "\n\n" + traceback.format_exc(),
                                                  encoding="utf-8")
                job.state = "failed"

    def list(self) -> list[dict]:
        return [j.to_dict() for j in sorted(self.jobs.values(), key=lambda j: j.id, reverse=True)]

    def get(self, job_id: str) -> Job:
        job = self.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Không có việc này")
        return job

    def delete(self, job_id: str) -> None:
        job = self.get(job_id)
        if job.state == "running":
            raise HTTPException(409, "Đang xử lý, chờ xong rồi xoá")
        del self.jobs[job_id]
        shutil.rmtree(job.dir, ignore_errors=True)


def _open_browser(url: str) -> None:
    try:
        is_wsl = "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        is_wsl = False
    if is_wsl:  # the Windows browser reaches WSL's localhost
        subprocess.Popen(["explorer.exe", url], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    else:
        import webbrowser

        webbrowser.open(url)


def _already_running(port: int) -> bool:
    """A second click on the shortcut opens the running app instead of failing."""
    import urllib.request

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never via a proxy
    try:
        with opener.open(f"http://127.0.0.1:{port}/", timeout=2) as resp:
            return b"Bokin Suno Master" in resp.read(2000)
    except OSError:
        return False


def create_app(token: str, out_dir: Path, port: int = DEFAULT_PORT,
               extra_hosts: tuple[str, ...] = ()) -> FastAPI:
    app = FastAPI(title="Bokin Suno Master", docs_url=None, redoc_url=None, openapi_url=None)
    jobs = Jobs(Path(out_dir).resolve())
    state = {"server": None}
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}", *extra_hosts}

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.headers.get("host", "") not in allowed_hosts:
            return JSONResponse({"detail": "bad host"}, status_code=403)
        if request.url.path == "/favicon.ico":
            return Response(status_code=204)
        if request.url.path != "/":
            supplied = request.headers.get("x-bokin-token") or request.query_params.get("t")
            if not supplied or not secrets.compare_digest(supplied, token):
                return JSONResponse({"detail": "missing or wrong token"}, status_code=403)
        return await call_next(request)

    @app.get("/", response_class=HTMLResponse)
    def index():
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        return html.replace("__BOKIN_TOKEN__", token)

    @app.get("/api/info")
    def info():
        return {"version": __version__, "out_dir": str(jobs.dir), "formats": list(FORMATS),
                "extensions": sorted(AUDIO_EXTENSIONS),
                "presets": {name: preset(name).to_dict() for name in PRESETS}}

    @app.post("/api/jobs")
    def add_job(song: UploadFile = File(...), reference: UploadFile | None = File(None),
                settings: str = Form("{}")):
        try:
            parsed = Settings.from_dict(json.loads(settings))
            parsed.check()
        except (ValueError, json.JSONDecodeError) as err:
            raise HTTPException(400, f"Cài đặt không hợp lệ: {err}") from err
        for upload in (song, reference):
            if upload is not None and Path(upload.filename or "").suffix.lower() not in AUDIO_EXTENSIONS:
                raise HTTPException(400, f"Không đọc được loại file này: {upload.filename}")
        return jobs.add(song, reference, parsed).to_dict()

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

    @app.get("/api/files/{job_id}/{name}")
    def get_file(job_id: str, name: str, download: bool = False):
        job = jobs.get(job_id)
        if name not in job.files.values():
            raise HTTPException(404, "Không có file này")
        return FileResponse(job.dir / name, filename=name if download else None,
                            content_disposition_type="attachment" if download else "inline")

    @app.post("/api/shutdown")
    def shutdown():
        if state["server"] is not None:
            state["server"].should_exit = True
        return {"stopping": True}

    app.state.bokin = state
    app.state.jobs = jobs
    return app


def run_app(port: int = DEFAULT_PORT, open_browser: bool = False, out_dir: str | Path = "outputs") -> None:
    import uvicorn

    url = f"http://localhost:{port}/"
    if _already_running(port):
        print(f"Bokin Suno Master is already running on {url}")
        if open_browser:
            _open_browser(url)
        return
    token = secrets.token_urlsafe(24)
    app = create_app(token, Path(out_dir), port=port)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    app.state.bokin["server"] = server
    print(f"Bokin Suno Master {__version__} on {url}  (Ctrl+C or the 'Tắt app' button to quit)")
    print(f"Results go to {Path(out_dir).resolve()}")
    if open_browser:
        threading.Timer(1.5, _open_browser, args=(url,)).start()
    server.run()
