"""Bokin Suno Studio end to end, with a real Chrome and the stand-in Suno (tests/fake_suno.py): every button of the
page pressed as a person would.

- Tài khoản Suno: Đăng nhập, Kiểm tra (one account), Kiểm tra đăng nhập (all), Đăng nhập lại, Xoá.
- Tải nhạc: Chọn… (the folder dialog), Mở thư mục, Xem danh sách bài (a workspace, and a share link: one song, never
  the Similar list beside it), Tải về (a few songs; someone else's song in the workspace skipped), Dừng, Làm mới,
  and on a downloaded song: Nghe, Lời (kept as text: a lyric line that looks like HTML stays text), Chép lời gốc,
  Đổi lời bài này, Đổi lời, Master (with a Kiểu master).
- Đổi lời: Lời Đồng Âm in the app's look, the song's lyrics respelled, its Chép lời.
- Master: the song mastered in Bokin Suno Master's page, Mở thư mục Master.
- The header: the update button once an update is ready, Tắt app.
- And on a computer with no key: the activation screen, Chép mã máy, Kích hoạt.

Needs Google Chrome (or BOKIN_STUDIO_CHROME: a Chrome or Chromium program); skipped without one. On Linux without a
screen: xvfb-run -a python -m pytest tests/studio/test_e2e.py
"""
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from fake_suno import WORKSPACE, FakeSuno  # noqa: E402

from bokin_studio.suno_tasks import chrome_path  # noqa: E402

CHROME = os.environ.get("BOKIN_STUDIO_CHROME") or chrome_path()
pytestmark = pytest.mark.skipif(not CHROME, reason="needs Google Chrome")
LICENSED = {"licensed": True, "message": "", "machine": "TEST", "expires": None, "soon": 14, "products": []}


def serve(app_kwargs):
    import uvicorn

    from bokin_studio.app import create_app

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(16)
    port = sock.getsockname()[1]
    app = create_app("e2e", port=port, **app_kwargs)
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    time.sleep(0.5)
    return app, server, f"http://127.0.0.1:{port}/"


@pytest.fixture
def studio(tmp_path, monkeypatch):
    from bokin_studio import app as studio_app
    from bokin_studio import licensing

    fake = FakeSuno()
    titles = ["Mưa đêm", "Mưa đêm", "Phố cũ", "Không lời"]
    ids = [fake.add_song(t, lyrics="" if t == "Không lời" else None) for t in titles]
    theirs = fake.add_song("Bài của người khác", owner="other")  # in the workspace, by someone else
    fake.start()
    # Linux: Chrome refuses a --user-data-dir with a long path, so the Suno data folder stays short
    short = Path(os.environ.get("TEMP", "/tmp")) if os.name == "nt" else Path("/tmp")
    suno_data = Path(tempfile.mkdtemp(prefix="ss-", dir=short))
    monkeypatch.setenv("BOKIN_SUNO_URL", fake.url)
    monkeypatch.setenv("BOKIN_SUNO_LOGIN_SETTLE", "2")
    if os.environ.get("BOKIN_STUDIO_CHROME") is None and CHROME != chrome_path():
        monkeypatch.setenv("BOKIN_STUDIO_CHROME", CHROME)
    monkeypatch.setattr(licensing, "licensed", lambda fresh=False: True)
    monkeypatch.setattr(licensing, "view", lambda fresh=False: LICENSED)
    music = tmp_path / "Nhạc của tôi"
    opened, picked = [], []
    monkeypatch.setattr(studio_app, "open_in_explorer", lambda path: opened.append(Path(path)))

    def pick(start=""):  # (Windows' own dialog has its own test: test_pick_folder.py)
        picked.append(start)
        return str(music)

    monkeypatch.setattr(studio_app, "pick_folder", pick)
    monkeypatch.setattr(studio_app, "can_pick", lambda: True)
    app, server, url = serve({"desktop": True, "suno_data": suno_data, "master_out": tmp_path / "master"})
    yield {"url": url, "fake": fake, "ids": ids, "theirs": theirs, "music": music, "app": app, "opened": opened,
           "picked": picked, "master": tmp_path / "master"}
    app.state.suno.shutdown()
    server.should_exit = True
    fake.stop()
    shutil.rmtree(suno_data, ignore_errors=True)


def browser_page(pw, errors):
    kw = {"executable_path": CHROME} if os.environ.get("BOKIN_STUDIO_CHROME") else {"channel": "chrome"}
    browser = pw.chromium.launch(headless=True, **kw)
    context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.dialogs = {"seen": [], "dismiss": False}  # the confirm() of Xoá, Tắt app, Tải về with stems: accepted

    def answer(d):
        page.dialogs["seen"].append(d.message)
        d.dismiss() if page.dialogs["dismiss"] else d.accept()
    page.on("dialog", answer)
    return browser, page


def run_task(page, button, seconds=300, wait=True):
    """Clicks a button that starts a Suno task; waits until that task (not the one before) has ended."""
    before = page.locator("#task").get_attribute("data-task") or ""
    if isinstance(button, str):
        page.click(button)
    else:
        button.click()
    page.wait_for_function("(before) => { const t = document.getElementById('task'); return t.dataset.task && "
                           "t.dataset.task !== before; }", arg=before, timeout=30_000)
    if wait:
        page.wait_for_function("() => /state-(done|failed|stopped)/.test(document.getElementById('taskState')"
                               ".className)", timeout=seconds * 1000)
    return page.locator("#taskState").get_attribute("class")


def account_task_done(page, seconds=120):
    page.wait_for_function("() => { const p = document.querySelector('#accountTask pre'); return p && "
                           "/state-(done|failed|stopped)/.test(document.getElementById('taskState').className); }",
                           timeout=seconds * 1000)
    return page.locator("#accountTask").inner_text()


def clipboard(page):
    """What was copied, with Windows' line breaks (Chrome writes \\r\\n there) as \\n."""
    return page.evaluate("() => navigator.clipboard.readText()").replace("\r\n", "\n")


def test_every_button(studio):
    from patchright.sync_api import sync_playwright

    fake, music = studio["fake"], studio["music"]
    link = f"{fake.url}/create?wid={WORKSPACE}"
    errors = []
    with sync_playwright() as pw:
        browser, page = browser_page(pw, errors)
        page.goto(studio["url"])
        assert page.locator("header h1 img").evaluate("i => i.naturalWidth") > 0, "the app's logo"
        assert page.locator('link[rel="icon"]').get_attribute("href") == "/logo.svg"

        # ---- 1. Tài khoản Suno ----
        page.locator("#view-accounts").wait_for(state="visible")  # no account yet: this tab first
        page.fill("#newAccount", "suno1")
        page.click("#login")
        page.wait_for_function("() => [...document.querySelectorAll('#accounts td')].some(t => t.textContent === "
                               "'suno1')", timeout=120_000)
        assert "Đã lưu tài khoản suno1" in account_task_done(page)
        assert fake.signins == 1
        row = page.locator("#accounts tr", has_text="suno1")
        run_task(page, row.get_by_role("button", name="Kiểm tra"))
        assert "suno1: đang đăng nhập" in account_task_done(page)
        run_task(page, "#checkAll")
        assert "suno1: đang đăng nhập" in account_task_done(page)
        run_task(page, row.get_by_role("button", name="Đăng nhập lại"))
        assert "Đã lưu tài khoản suno1" in account_task_done(page)

        # ---- 2. Tải nhạc ----
        page.click("nav button[data-view=download]")
        page.select_option("#account", "suno1")
        page.fill("#links", link)
        page.click("#pickFolder")
        page.wait_for_function("(want) => document.getElementById('folder').value === want", arg=str(music))
        assert studio["picked"], "Chọn… opened the folder dialog"
        assert "state-done" in run_task(page, "#listSongs", 120)
        page.locator("#listed").wait_for(state="visible")
        listed = page.locator("#listed tbody tr").all_inner_texts()
        assert len(listed) == 5 and any("Phố cũ" in t for t in listed)

        # a share link (suno.com/s/...): that one song, not the Similar list beside it
        page.fill("#links", f"{fake.url}/s/{fake.add_share(studio['ids'][2])}")
        assert "state-done" in run_task(page, "#listSongs", 120)
        page.wait_for_function("() => document.querySelectorAll('#listed tbody tr').length === 1")
        assert "1 bài" in page.locator("#taskLog").inner_text()

        page.fill("#links", link)
        page.fill("#limit", "4")
        assert "state-done" in run_task(page, "#download")
        log = page.locator("#taskLog").inner_text()
        assert "3 bài tải xong" in log and "1 bài của người khác (bỏ qua)" in log, log
        assert studio["theirs"] not in fake.counted and studio["theirs"] not in [s for s, _ in fake.picked]
        page.wait_for_function("() => document.querySelectorAll('#library tbody tr').length === 3")
        rows = page.locator("#library tbody tr")
        assert sorted(rows.locator("td:first-child").all_inner_texts()) == sorted(["Không lời", "Phố cũ", "Mưa đêm"])

        page.click("#openFolder")
        time.sleep(0.5)
        assert music in studio["opened"], "Mở thư mục opened the music folder"

        # Nghe
        rows.filter(has_text="Phố cũ").get_by_role("button", name="Nghe").click()
        page.wait_for_function("() => { const p = document.getElementById('player'); return !p.hidden && "
                               "p.readyState >= 1 && !p.error; }", timeout=20_000)

        # Lời, Chép lời gốc
        assert rows.filter(has_text="Không lời").get_by_role("button", name="Lời", exact=True).is_disabled()
        rows.filter(has_text="Phố cũ").get_by_role("button", name="Lời", exact=True).click()
        page.locator("#lyricsText").wait_for(state="visible")
        text = page.locator("#lyricsText").inner_text()
        assert "Silent night, holy night" in text and "<img src=x" in text
        assert page.locator("#lyricsText img").count() == 0 and page.title() == "Bokin Suno Studio"
        page.click("#copyLyrics")
        page.wait_for_function("() => document.getElementById('toast').textContent.includes('Đã chép lời gốc')")
        assert clipboard(page).startswith("[Verse]\nSilent night, holy night")

        # Đổi lời bài này → the Đổi lời tab, the song's lyrics respelled; its own Chép lời
        page.click("#respell")
        frame = page.frame_locator("#lyricsFrame")
        page.wait_for_function("() => { const d = document.getElementById('lyricsFrame').contentDocument; "
                               "return d && d.getElementById('src') && d.getElementById('src').value.includes("
                               "'Silent night') && d.getElementById('out').textContent.includes('Verse]'); }",
                               timeout=30_000)
        out = frame.locator("#out").inner_text()
        assert "[Verse]" in out and out != text
        assert "Phố cũ" in page.locator("#lyricsFrom").inner_text()
        assert frame.locator("#out img").count() == 0
        assert not frame.locator(".masthead h1").is_visible(), "Lời Đồng Âm in the app's look (no title of its own)"
        assert frame.locator(".notice").is_visible(), "the Public Domain reminder stays"
        frame.locator("#copy").click()
        page.wait_for_function("() => navigator.clipboard.readText().then(t => t.includes('[Chorus]'))")
        assert clipboard(page) != text

        # Đổi lời on another song's row
        page.click("nav button[data-view=download]")
        rows.filter(has_text="Mưa đêm").get_by_role("button", name="Đổi lời").click()
        page.wait_for_function("() => document.getElementById('lyricsFrom').textContent.includes('Mưa đêm')")
        page.wait_for_function("() => document.getElementById('lyricsFrame').contentDocument.getElementById('src')"
                               ".value.includes('Mưa đêm')", timeout=10_000)

        # Dừng: a download of several songs stopped after the one being downloaded
        page.click("nav button[data-view=download]")
        more = [fake.add_song(f"Bài thêm {n}") for n in range(1, 6)]
        page.fill("#limit", "")
        run_task(page, "#download", wait=False)
        page.wait_for_function("() => /Bài [1-9]\\/\\d/.test(document.getElementById('taskCount').textContent)",
                               timeout=60_000)
        page.click("#stop")
        page.wait_for_function("() => /state-(done|failed|stopped)/.test(document.getElementById('taskState')"
                               ".className)", timeout=120_000)
        assert "state-stopped" in page.locator("#taskState").get_attribute("class")
        got = sum(1 for s in more if s in fake.counted)
        assert 1 <= got < len(more), f"stopped after {got} of {len(more)}"

        # Làm mới
        page.click("#refreshLibrary")
        page.wait_for_function("(n) => document.querySelectorAll('#library tbody tr').length === n", arg=3 + got)

        # Master: Kiểu master, the row's Master button, the Master tab, Mở thư mục Master
        page.select_option("#preset", "jazz")
        rows.filter(has_text="Phố cũ").get_by_role("button", name="Master").click()
        page.click("nav button[data-view=master]")
        master = page.frame_locator("#masterFrame")
        master.locator(".job").first.wait_for(timeout=30_000)
        master.locator(".job .state-done").first.wait_for(timeout=180_000)
        assert "Phố cũ" in master.locator(".job").first.inner_text()
        assert not master.locator("header").first.is_visible()
        jobs = studio["app"].state.jobs.list()
        assert jobs[0]["state"] == "done" and jobs[0]["files"]["master"].endswith("_master.wav")
        from bokin_suno.master import preset
        used = json.loads((studio["master"] / jobs[0]["id"] / "settings.json").read_text(encoding="utf-8"))
        assert used["settings"] == preset("jazz").to_dict(), "the Kiểu master chosen (Jazz)"
        page.click("#openMaster")
        time.sleep(0.5)
        assert studio["master"].resolve() in [p.resolve() for p in studio["opened"]], "Mở thư mục Master"

        # Xoá the account
        page.click("nav button[data-view=accounts]")
        run_task(page, page.locator("#accounts tr", has_text="suno1").get_by_role("button", name="Xoá"))
        page.wait_for_function("() => !document.getElementById('noAccounts').hidden", timeout=30_000)

        # the header: an update ready, then Tắt app
        shared = studio["app"].state.bokin

        class Ready:
            state = {"current": "1.0.0", "available": "9.9.9", "ready": True, "error": None, "reason": None,
                     "checked": time.time(), "downloading": None}

        shared.updater = Ready()
        page.evaluate("() => location.reload()")
        page.wait_for_function("() => document.getElementById('update').textContent.includes('Có bản mới 9.9.9')",
                               timeout=30_000)
        page.click("#quit")
        page.wait_for_function("() => document.body.textContent.includes('Đã tắt app')", timeout=10_000)
        assert shared.quit.is_set()

        assert not errors, errors
        browser.close()
    assert fake.buy_clicks == 0


@pytest.mark.unlicensed
def test_activation_screen(request, tmp_path):
    """No key on this computer: the activation screen, Chép mã máy, a key pasted, Kích hoạt, then the app."""
    from patchright.sync_api import sync_playwright

    from bokin_studio import licensing
    from tests.conftest import signed_key

    app, server, url = serve({"suno_data": tmp_path / "suno", "master_out": tmp_path / "master"})
    errors = []
    try:
        with sync_playwright() as pw:
            browser, page = browser_page(pw, errors)
            page.goto(url)
            page.locator("#licenceView").wait_for(state="visible")
            assert page.locator("#tabs").is_hidden()
            machine = page.locator("#machine").inner_text()
            assert machine == licensing.view()["machine"]
            page.click("#copyMachine")
            page.wait_for_function("() => document.getElementById('toast').textContent.includes('Đã chép mã máy')")
            assert clipboard(page) == machine
            page.click("#activate")  # no key yet
            page.wait_for_function("() => document.getElementById('toast').textContent.includes('Hãy dán key')")
            page.fill("#licenceKey", signed_key(request, ("suno-master",)))  # another app's key
            page.click("#activate")
            page.wait_for_function("() => document.getElementById('licenceView').hidden === false && "
                                   "document.getElementById('toast').style.display === 'block'")
            page.fill("#licenceKey", signed_key(request, ("suno-studio",)))
            page.click("#activate")
            page.locator("#tabs").wait_for(state="visible", timeout=20_000)
            assert page.locator("#licenceView").is_hidden()
            assert not errors, errors
            browser.close()
    finally:
        app.state.suno.shutdown()
        server.should_exit = True


def test_stems_button(studio):
    """A song downloaded before: its Stems button (the song's stems not made yet: Extract pressed on Suno, after the
    box asking first), the stems unpacked next to it, then its Mở stems button; the stems checkbox kept."""
    import csv

    from patchright.sync_api import sync_playwright

    fake, music, sid = studio["fake"], studio["music"], studio["ids"][2]
    fake.config["extract_confirm"] = True
    music.mkdir(parents=True)
    (music / "Phố cũ.wav").write_bytes(b"RIFF" + bytes(4000))
    with open(music / "danh-sach.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ten_bai", "file", "trang_thai", "ghi_chu", "dinh_dang", "link", "luc", "id"])
        w.writerow(["Phố cũ", "Phố cũ.wav", "xong", "", "wav", f"{fake.url}/song/{sid}", "2026-10-30 10:00:00", sid])
    errors = []
    with sync_playwright() as pw:
        browser, page = browser_page(pw, errors)
        page.goto(studio["url"])
        page.locator("#view-accounts").wait_for(state="visible")
        page.fill("#newAccount", "suno1")
        page.click("#login")
        page.wait_for_function("() => [...document.querySelectorAll('#accounts td')].some(t => t.textContent === "
                               "'suno1')", timeout=120_000)
        page.click("nav button[data-view=download]")
        page.fill("#folder", str(music))
        page.dispatch_event("#folder", "change")
        page.check("#stems")
        page.dispatch_event("#folder", "change")  # (saves the settings)
        page.wait_for_function("() => document.querySelectorAll('#library tbody tr').length === 1")
        row = page.locator("#library tbody tr", has_text="Phố cũ")
        assert "state-done" in run_task(page, row.get_by_role("button", name="Stems", exact=True))
        log = page.locator("#taskLog").inner_text()
        assert "stems xong" in log and "Phố cũ - stems" in log, log
        assert fake.extract_clicks == [sid] and fake.stems_downloads[-1] == (sid, "wav,mp3,midi", "follow")
        stems = music / "Phố cũ - stems"
        assert (stems / "WAV" / "Drums.wav").is_file() and (stems / "MIDI" / "Drums.mid").is_file()
        page.wait_for_function("() => [...document.querySelectorAll('#library tbody button')].some(b => "
                               "b.textContent === 'Mở stems')", timeout=30_000)
        page.locator("#library tbody tr", has_text="Phố cũ").get_by_role("button", name="Mở stems").click()
        time.sleep(0.5)
        assert stems in studio["opened"]
        # Tải về with the stems checkbox ticked asks first (credits): Cancel starts nothing
        page.fill("#links", f"{fake.url}/create?wid=x")
        page.fill("#limit", "1")
        page.dialogs["dismiss"] = True
        before = page.locator("#task").get_attribute("data-task")
        page.click("#download")
        time.sleep(1)
        page.dialogs["dismiss"] = False
        asked = page.dialogs["seen"][-1] if page.dialogs["seen"] else ""
        assert "credit" in asked and "tối đa 1 bài" in asked, asked
        assert page.locator("#task").get_attribute("data-task") == before, "nothing started"
        page.reload()
        page.click("nav button[data-view=download]")
        assert page.locator("#stems").is_checked(), "the stems checkbox kept"
        assert fake.pressed == [] and not errors, (fake.pressed, errors)
        browser.close()
