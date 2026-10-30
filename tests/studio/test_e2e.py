"""Bokin Suno Studio end to end, with a real Chrome and the stand-in Suno (tests/fake_suno.py): the page as a person
uses it. Add a Suno account (sign in), list a workspace, download a few songs, see a song's lyrics (kept as text: a
lyric line that looks like HTML stays text), respell them in Lời Đồng Âm, send the song to Master and get it mastered.

Needs Google Chrome (or BOKIN_STUDIO_CHROME: a Chrome or Chromium program); skipped without one. On Linux without a
screen: xvfb-run -a python -m pytest tests/studio/test_e2e.py
"""
import os
import socket
import sys
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


@pytest.fixture
def studio(tmp_path, monkeypatch):
    import uvicorn

    from bokin_studio import licensing
    from bokin_studio.app import create_app

    fake = FakeSuno()
    titles = ["Mưa đêm", "Mưa đêm", "Phố cũ", "Không lời"]
    ids = [fake.add_song(t, lyrics="" if t == "Không lời" else None) for t in titles]
    fake.start()
    # Linux: Chrome refuses a --user-data-dir with a long path, so the Suno data folder stays short
    short = Path(os.environ.get("TEMP", "/tmp")) if os.name == "nt" else Path("/tmp")
    suno_data = Path(__import__("tempfile").mkdtemp(prefix="ss-", dir=short))
    monkeypatch.setenv("BOKIN_SUNO_URL", fake.url)
    monkeypatch.setenv("BOKIN_SUNO_LOGIN_SETTLE", "2")
    if os.environ.get("BOKIN_STUDIO_CHROME") is None and CHROME != chrome_path():
        monkeypatch.setenv("BOKIN_STUDIO_CHROME", CHROME)
    monkeypatch.setattr(licensing, "licensed", lambda fresh=False: True)
    monkeypatch.setattr(licensing, "view", lambda fresh=False: {"licensed": True, "message": "", "machine": "TEST",
                                                                "expires": None, "soon": 14, "products": []})
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(16)
    port = sock.getsockname()[1]
    app = create_app("e2e", port=port, suno_data=suno_data, master_out=tmp_path / "master")
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    time.sleep(0.5)
    yield {"url": f"http://127.0.0.1:{port}/", "fake": fake, "ids": ids, "music": tmp_path / "Nhạc",
           "suno_data": suno_data, "app": app}
    app.state.suno.shutdown()
    server.should_exit = True
    fake.stop()
    import shutil
    shutil.rmtree(suno_data, ignore_errors=True)


def run_task(page, button, seconds=300):
    """Clicks a button that starts a Suno task, waits until that task (not the one before) has ended."""
    before = page.locator("#task").get_attribute("data-task") or ""
    page.click(button)
    page.wait_for_function("(before) => { const t = document.getElementById('task'); "
                           "const s = document.getElementById('taskState'); return t.dataset.task && "
                           "t.dataset.task !== before && /state-(done|failed|stopped)/.test(s.className); }",
                           arg=before, timeout=seconds * 1000)
    return page.locator("#taskState").get_attribute("class")


def test_studio_end_to_end(studio):
    from patchright.sync_api import sync_playwright

    fake = studio["fake"]
    link = f"{fake.url}/create?wid={WORKSPACE}"
    with sync_playwright() as pw:
        kw = {"executable_path": CHROME} if os.environ.get("BOKIN_STUDIO_CHROME") else {"channel": "chrome"}
        browser = pw.chromium.launch(headless=True, **kw)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(studio["url"])

        # 1. no account yet: the Accounts tab; sign in
        page.locator("#view-accounts").wait_for(state="visible")
        page.fill("#newAccount", "suno1")
        page.click("#login")
        page.wait_for_function("() => [...document.querySelectorAll('#accounts td')].some(t => t.textContent === "
                               "'suno1')", timeout=120_000)
        assert fake.signins == 1

        # 2. list, then download three songs (WAV) into a folder of our own
        page.click("nav button[data-view=download]")
        page.select_option("#account", "suno1")
        page.fill("#links", link)
        page.fill("#folder", str(studio["music"]))
        page.dispatch_event("#folder", "change")
        assert "state-done" in run_task(page, "#listSongs", 120)
        page.locator("#listed").wait_for(state="visible")
        listed = page.locator("#listed tbody tr").all_inner_texts()
        assert len(listed) == 4 and any("Phố cũ" in t for t in listed)
        page.fill("#limit", "3")
        assert "state-done" in run_task(page, "#download")
        assert "3 bài tải xong" in page.locator("#taskLog").inner_text()
        page.wait_for_function("() => document.querySelectorAll('#library tbody tr').length === 3")
        rows = page.locator("#library tbody tr")
        assert sorted(rows.locator("td:first-child").all_inner_texts()) == sorted(["Không lời", "Phố cũ", "Mưa đêm"])

        # 3. the lyrics of a song: shown as text, then respelled in Lời Đồng Âm
        row = rows.filter(has_text="Phố cũ")
        assert rows.filter(has_text="Không lời").get_by_role("button", name="Lời", exact=True).is_disabled()
        row.get_by_role("button", name="Lời", exact=True).click()
        page.locator("#lyricsText").wait_for(state="visible")
        text = page.locator("#lyricsText").inner_text()
        assert "Silent night, holy night" in text and "<img src=x" in text
        assert page.locator("#lyricsText img").count() == 0 and page.title() == "Bokin Suno Studio"
        page.click("#respell")
        frame = page.frame_locator("#lyricsFrame")
        frame.locator("#src").wait_for()
        page.wait_for_function("() => { const d = document.getElementById('lyricsFrame').contentDocument; "
                               "return d && d.getElementById('src').value.includes('Silent night') && "
                               "d.getElementById('out').textContent.includes('Verse]'); }", timeout=30_000)
        out = frame.locator("#out").inner_text()
        assert "[Verse]" in out and out != text  # tags kept, words respelled
        assert "Phố cũ" in page.locator("#lyricsFrom").inner_text()
        assert page.frame_locator("#lyricsFrame").locator("#out img").count() == 0

        # 4. Master: the song sent from the list, mastered in the Master tab
        page.click("nav button[data-view=download]")
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

        assert not errors, errors
        browser.close()
    assert fake.buy_clicks == 0
    assert sorted(fake.counted) == sorted(fake.workspace[:3])
