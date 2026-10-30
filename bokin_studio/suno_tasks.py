"""The Suno side of Bokin Suno Studio: the downloader's command line (suno/bokin_suno.py) run as a program of its
own for each task (sign in, check, list, download, remove an account), one task at a time, its output read back
for the page.

The command line is `BokinSunoStudio.exe suno ...` in the installed app (desktop.run_suno) and `python -m
bokin_studio suno ...` from the source folder. Its data folder (accounts, a Chrome profile per Suno account, logs)
is the app's suno\\ folder. Everything Suno-side keeps the command line's rules: only Suno's own Download button,
never Buy/Upgrade, stop when the plan's downloads are used up.

Stop: a download (or a Stems & MIDI task) stops before its next song once the stop file exists (BOKIN_SUNO_STOP),
never in the middle of a song (Suno has counted its download, or its stems' credits, by then); only one that has not
stopped long after the longest a song can take is ended. Any other task (a sign-in waiting for its window) is ended
at once.
"""

import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

PROGRESS = re.compile(r"^\d\d:\d\d:\d\d  \[(\d+)/(\d+)\] ")  # "12:00:00  [3/20] Title: ...", not a title's own [3/4]
STEMS_START = re.compile(r"^\d\d:\d\d:\d\d  Stems & MIDI \(.*\): (\d+) bài cần tải")  # then [n/N] count the stems
LISTED = re.compile(r"^(\d+)\t(.*)\t(https?://\S+)$")
KEEP_LINES = 400
STOP_GRACE = 15 * 60  # seconds a download has to stop by itself (one song: up to 2 x 5 minutes) before it is ended
# a task with stems: they stop while Suno makes them too, and once their files' Download is pressed they have up to
# 10 minutes to arrive (suno/web.py FILES_WAIT), then they are unpacked
STEMS_STOP_GRACE = 25 * 60
BY_SONG = ("download", "stems")  # the tasks that stop between two songs


class Busy(Exception):
    pass


def suno_command():
    """The program that runs the Suno command line."""
    if os.environ.get("BOKIN_STUDIO_SUNO_CMD"):  # (tests)
        import json
        return json.loads(os.environ["BOKIN_STUDIO_SUNO_CMD"])
    if getattr(sys, "frozen", False):
        return [sys.executable, "suno"]
    return [sys.executable, "-m", "bokin_studio", "suno"]


def chrome_path():
    """Google Chrome's program on this computer, or None (the Suno side needs it: patchright's channel "chrome")."""
    if os.name == "nt":
        for base in (os.environ.get(k) for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")):
            if base:
                path = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
                if os.path.exists(path):
                    return path
        return None
    import shutil
    for name in ("google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    return "/opt/google/chrome/chrome" if os.path.exists("/opt/google/chrome/chrome") else None


class Task:
    def __init__(self, kind, args, label):
        self.id = f"{int(time.time() * 1000)}"
        self.kind, self.args, self.label = kind, args, label
        self.state = "running"  # running, done, failed, stopped
        self.code = None
        self.lines = []
        self.first = 0  # how many lines were dropped from the front of `lines` (KEEP_LINES): line numbers go on
        self.songs = []  # the songs a "list" printed: {"n", "title", "link"}
        self.done = self.total = 0
        self.phase = ""  # "stems" once a download's Stems & MIDI (or a stems task) has started
        self.started, self.ended = time.time(), None
        self.stopping = False
        self.proc = None
        self.stop_file = None

    def to_dict(self, since=0, songs=True):
        """since: the number of lines the page has already (line numbers count from the task's start)."""
        first, lines = self.first, list(self.lines)  # (one look: the reader thread may add lines meanwhile)
        return {"id": self.id, "kind": self.kind, "label": self.label, "state": self.state, "code": self.code,
                "lines": lines[max(0, since - first):], "line_count": first + len(lines),
                "songs": self.songs if songs and self.state != "running" else [],
                "song_count": len(self.songs), "done": self.done, "total": self.total, "phase": self.phase,
                "started": self.started,
                "ended": self.ended, "stopping": self.stopping}


class SunoTasks:
    def __init__(self, data_dir: Path):
        self.data = Path(data_dir)
        self.data.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.task = None  # the running or last task
        self.work = Path(tempfile.mkdtemp(prefix="bokin-studio-"))

    def busy(self):
        return bool(self.task and self.task.state == "running")

    def start(self, kind, args, label, headless=False, chrome=None):
        with self.lock:
            if self.busy():
                raise Busy(f"Đang chạy: {self.task.label}. Chờ xong (hoặc bấm Dừng) rồi làm tiếp.")
            task = Task(kind, list(args), label)
            self.task = task
        try:
            # (the temporary folder again each time: Windows' cleanup may have emptied it while the app was open)
            self.work.mkdir(parents=True, exist_ok=True)
            out = self.work / f"{task.id}.log"
            task.stop_file = self.work / f"{task.id}.stop"
            out.write_text("", encoding="utf-8")
            command = suno_command() + ["--data", str(self.data)]
            if headless:
                command.append("--headless")
            if chrome:
                command += ["--chrome", chrome]
            command += [kind] + task.args
            env = dict(os.environ, BOKIN_STUDIO_OUTPUT=str(out), BOKIN_SUNO_STOP=str(task.stop_file),
                       PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            task.proc = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, creationflags=flags)
        except Exception as e:  # noqa: BLE001 - never a task left "running" with nothing running
            task.lines.append(f"Không chạy được phần tải nhạc: {type(e).__name__}: {e}")
            task.state, task.ended = "failed", time.time()
            return task
        threading.Thread(target=self._follow, args=(task, out), daemon=True, name="suno-task").start()
        return task

    def _follow(self, task, out):
        """Reads the program's output as it is written, until it has ended and everything is read."""
        with open(out, encoding="utf-8", errors="replace", newline="") as f:
            partial = ""
            while True:
                ended = task.proc.poll() is not None
                chunk = f.read()
                if chunk:
                    partial += chunk
                    *full, partial = partial.split("\n")
                    for line in full:
                        self._line(task, line.rstrip("\r"))
                elif ended:
                    break
                else:
                    time.sleep(0.2)
            if partial.strip():
                self._line(task, partial.rstrip("\r"))
        task.code = task.proc.returncode
        task.ended = time.time()
        task.state = "stopped" if task.stopping else ("done" if task.code == 0 else "failed")
        for path in (out, getattr(task, "stop_file", None)):
            try:
                if path:
                    path.unlink()
            except OSError:
                pass

    def _line(self, task, line):
        listed = LISTED.match(line)
        if listed:
            task.songs.append({"n": int(listed.group(1)), "title": listed.group(2), "link": listed.group(3)})
            return
        m = PROGRESS.search(line)
        if m:
            task.done, task.total = int(m.group(1)), int(m.group(2))
        m = STEMS_START.search(line)
        if m:
            task.phase, task.done, task.total = "stems", 0, int(m.group(1))
        task.lines.append(line)
        if len(task.lines) > KEEP_LINES:
            drop = len(task.lines) - KEEP_LINES
            del task.lines[:drop]
            task.first += drop

    def stop(self):
        """Stop the running task: a download after its current song, anything else now."""
        task = self.task
        if not task or task.state != "running":
            return False
        task.stopping = True
        if task.kind in BY_SONG and task.stop_file:
            try:
                task.stop_file.write_text("", encoding="utf-8")
            except OSError:
                pass
            grace = STEMS_STOP_GRACE if task.kind == "stems" or "--stems" in task.args else STOP_GRACE
            threading.Thread(target=self._end_later, args=(task, grace), daemon=True).start()
        else:
            self._end(task)
        return True

    def _end_later(self, task, seconds):
        deadline = time.time() + seconds
        while time.time() < deadline and task.proc.poll() is None:
            time.sleep(0.5)
        self._end(task)

    @staticmethod
    def _end(task):
        if task.proc and task.proc.poll() is None:
            task.proc.terminate()
            try:
                task.proc.wait(10)
            except subprocess.TimeoutExpired:
                task.proc.kill()

    def shutdown(self):
        """The app is quitting: end a running task (its Chrome closes with it)."""
        task = self.task
        if task and task.state == "running":
            task.stopping = True
            self._end(task)

    def accounts(self):
        import json
        try:
            value = json.loads((self.data / "accounts.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [{"name": name, "added": (rec or {}).get("added", "")} for name, rec in sorted(value.items())]
