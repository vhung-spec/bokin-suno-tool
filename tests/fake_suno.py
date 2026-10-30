"""A stand-in suno.com for the tests: sign-in, a workspace's song list, a song page with its Download menu and box.

It copies only what the program touches (suno/web.py SEL): window.Clerk for the sign-in state (or, with
config["clerk_global"] off, as suno.com showed on the owner's computer, none: only Clerk's cookies __client_uat and
__session, a token whose "sub" is the user id), song links in a
scrolling list that loads more as it scrolls (or by a Load more button, or in pages behind Previous page / Next page
buttons, Next page left enabled on the last page as on suno.com's Create page) and drops rows scrolled far away, a
player bar with a link to a song not in the workspace, a "Download cover image" button on the song's cover, the song's
More options menu with suno.com's items (Move to Trash among them, never to be pressed), Download → MP3 Audio / WAV
Audio, the WAV box that
prepares the file before its Download File button works, an optional "uses 1 download" box for MP3, the box saying
the plan's downloads are used up, with a Buy button that must never be pressed, song pages that fail once
(`fail_once`), the lyrics on a song page (none for an instrumental), and as on suno.com: share links (/s/<code>,
which the page's script sends on to the song's page), a Similar list of other people's songs beside every song, and
on other people's songs a Follow button by the artist's name. Downloading, as on suno.com in October 2026
(config["download_ui"] "box", the default): More options → Download opens a box "Download '<title>'" with rows M4A,
MP3, WAV, MP4 video asset, Stems & MIDI (a Manage button). A click on a row chooses or unchooses it, several can be
chosen at once (MP3 is, at first), and every chosen format is downloaded (here one file each). A chosen row shows a
check mark and nothing else says so (aria-pressed only with config["box_aria"]). Below: the plan's downloads left and
an "Unlock & Download" button ("Download" and "You've unlocked this song" once the song has been downloaded).
config["download_ui"] "menu" is the older menu: Download → WAV Audio / MP3 Audio and its boxes. Files arrive as a download
(from a blob or a link) or open in a new tab, as `config["delivery"]` says. Like Suno, a song counts as one download
whatever the format and however often it is downloaded.
"""
import base64
import hashlib
import html
import json
import secrets
import struct
import threading
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

USER_ID = "user_fakeBokinSuno0001"
WORKSPACE = "7b0c5f4e-ws01-4e4e-9c9c-000000000001"
PAGE_SIZE = 15


def audio_bytes(song_id, fmt):
    """The song's file: a short WAV (RIFF) or MP3 (ID3), different for every song."""
    seed = hashlib.sha256(f"{song_id}|{fmt}".encode()).digest()
    body = (seed * 700)[:20000]
    if fmt == "wav":
        return (b"RIFF" + struct.pack("<I", 36 + len(body)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000,
                16000, 2, 16) + b"data" + struct.pack("<I", len(body)) + body)
    return b"ID3\x04\x00\x00\x00\x00\x00\x00" + body


STEM_NAMES = ("Drums", "Bass", "Guitar", "Piano", "Vocals", "Other")


def stems_zip(song_id, files):
    """A song's Stems & MIDI as Suno would send them: one zip, a folder per kind, and a name trying to get out."""
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for kind in files:
            for name in STEM_NAMES:
                ext = {"wav": "wav", "mp3": "mp3", "midi": "mid"}[kind]
                z.writestr(f"{kind.upper()}/{name}.{ext}", audio_bytes(f"{song_id}-{name}", kind if kind != "midi"
                                                                        else "mp3")[:3000])
        z.writestr("../evil.txt", "a name that tries to leave the folder")
    return buf.getvalue()


def default_lyrics(title):
    """A song's lyrics: tags, verses, a blank line, and text that must stay text (lyrics are not trusted)."""
    return (f"[Verse]\nSilent night, holy night\nAll is calm, all is bright\n\n[Chorus]\n{title}\n"
            "<img src=x onerror=\"document.title='pwned'\"> & more")


class FakeSuno:
    def __init__(self):
        self.config = {"auto_signin": True, "user_id": USER_ID, "delivery": "blob", "confirm": False,
                       "downloads_left": None, "paging": "scroll", "prepare_ms": 800, "more_label": "More options",
                       "clerk_global": True, "download_ui": "box", "box_aria": False,
                       "credits": None, "extract_ms": 1500, "extract_confirm": False, "stems_aria": False,
                       # the stems box shows the song's stems this long after it opens (loading them from the server);
                       # nothing shown while the stems are made (no "Extracting..."); the box confirming Extract stays
                       # open this long after its Extract is pressed (the button still enabled); a kind left out of the
                       # stems zip; the kinds ticked at first in the files box (Suno remembering the last choice), its
                       # squares drawn as an svg (a check added when ticked); "Not enough credits" as a notice (toast)
                       "stems_load_ms": 0, "extract_silent": False, "confirm_close_ms": 0, "stems_drop": "",
                       "files_start": "mp3,wav,midi", "files_square": False, "credits_ui": "box"}
        self.sessions = set()
        self.signins = 0
        self.songs = {}
        self.workspace = []
        self.counted = []  # songs Suno counted as downloads (each song once)
        self.picked = []  # (song id, format) every time a format was chosen in the menu
        self.buy_clicks = 0
        self.pressed = []  # buttons the program must never press: Move to Trash, Download cover image, Manage
        self.fail_once = set()  # song pages that answer with an error the first time
        self.stems = {}  # song id -> "extracting" or "ready" (Stems & MIDI made on Suno)
        self.extract_clicks = []  # songs whose Extract was pressed (it may use credits)
        self.stems_downloads = []  # (song id, files, tempo) every time the stems' Download was pressed
        self.stems_opened = []  # songs whose Stems & MIDI → Manage was opened
        self.list_pages = []  # the pages of the workspace's list that were asked for
        self.lock = threading.Lock()
        self.stray = self.add_song("Bài đang phát", in_workspace=False)
        self.shares = {}  # share code -> song id
        self.similar = [self.add_song(f"Bài tương tự {n}", in_workspace=False, owner="other") for n in range(1, 7)]
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def stop(self):
        self.server.shutdown()

    def add_share(self, song_id):
        code = secrets.token_urlsafe(12)
        self.shares[code] = song_id
        return code

    def add_song(self, title, status="complete", in_workspace=True, lyrics=None, owner="me"):
        sid = str(uuid.uuid4())
        if lyrics is None:
            lyrics = default_lyrics(title)
        self.songs[sid] = {"title": title, "status": status, "lyrics": lyrics, "owner": owner}
        if in_workspace:
            self.workspace.insert(0, sid)  # newest first, as Suno lists them
        return sid

    def sign_everyone_out(self):
        self.sessions.clear()

    def _handler(self):
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _signed_in(self):
                for part in (self.headers.get("Cookie") or "").split(";"):
                    k, _, v = part.strip().partition("=")
                    if k == "__session" and v in fake.sessions:
                        return True
                return False

            def _send(self, code, body=b"", ctype="text/html; charset=utf-8", headers=()):
                if isinstance(body, str):
                    body = body.encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                for k, v in headers:
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def _page(self, body, script=""):
                user = json.dumps({"id": fake.config["user_id"]}) if self._signed_in() else "null"
                clerk = "Clerk" if fake.config["clerk_global"] else "__clerkInsideABundle"
                return self._send(200, PAGE.replace("__USER__", user).replace("__CLERK__", clerk).replace("__BODY__", body)
                                  .replace("__SCRIPT__", script))

            def do_GET(self):
                u = urlparse(self.path)
                q = parse_qs(u.query)
                parts = [p for p in u.path.split("/") if p]
                if u.path == "/sign-in":
                    return self._send(200, SIGNIN_PAGE)
                if u.path == "/":
                    auto = "true" if fake.config["auto_signin"] else "false"
                    return self._page('<h1>Explore</h1>' + ("" if self._signed_in() else SIGN_IN_BUTTON),
                                      f"setTimeout(() => {{ if (!document.cookie.includes('__client_uat=1') && {auto}) "
                                      f"location.href = "
                                      f"'/sign-in'; }}, 500);")
                if len(parts) == 2 and parts[0] == "s":
                    target = fake.shares.get(parts[1])
                    if not target:
                        return self._send(404, "not found")
                    return self._send(200, f"<!doctype html><title>Suno</title><p>Opening...</p><script>setTimeout("
                                           f"() => location.replace('/song/{target}'), 400)</script>")
                if len(parts) == 3 and parts[:2] == ["api", "stems"]:
                    time.sleep(min(60, int(q.get("wait", ["0"])[0] or 0)) / 1000)  # (a slow server)
                    return self._send(200, json.dumps({"state": fake.stems.get(parts[2], "none")}), "application/json")
                if len(parts) == 2 and parts[0] == "stemszip" and parts[1].endswith(".zip"):
                    sid = parts[1][:-4]
                    files = [f for f in q.get("files", [""])[0].split(",") if f in ("wav", "mp3", "midi")]
                    files = [f for f in files if f != fake.config["stems_drop"]]
                    if fake.stems.get(sid) != "ready" or not files:
                        return self._send(404, "not found")
                    return self._send(200, stems_zip(sid, files), "application/zip")
                if len(parts) == 2 and parts[0] in ("files", "cdn"):
                    sid, _, fmt = parts[1].rpartition(".")
                    if sid not in fake.songs or fmt not in ("wav", "mp3"):
                        return self._send(404, "not found")
                    ctype = "audio/wav" if fmt == "wav" else "audio/mpeg"
                    disp = (("Content-Disposition", f'attachment; filename="{sid}.{fmt}"'),) if parts[0] == "files" \
                        else ()
                    return self._send(200, audio_bytes(sid, fmt), ctype, disp)
                if not self._signed_in():
                    return self._page(SIGN_IN_BUTTON)
                if u.path == "/create":
                    if q.get("wid", [""])[0] != WORKSPACE:
                        return self._page("<h1>Create</h1><p>Workspace not found</p>")
                    cfg = json.dumps({"wid": WORKSPACE, "paging": fake.config["paging"], "stray": fake.stray})
                    return self._page(WORKSPACE_BODY, WORKSPACE_SCRIPT.replace("__CFG__", cfg))
                if len(parts) == 3 and parts[:2] == ["api", "ws"]:
                    page = int(q.get("page", ["0"])[0])
                    fake.list_pages.append(page)
                    ids = fake.workspace[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
                    out = {"songs": [{"id": s, "title": fake.songs[s]["title"]} for s in ids],
                           "more": (page + 1) * PAGE_SIZE < len(fake.workspace)}
                    return self._send(200, json.dumps(out), "application/json")
                if len(parts) == 2 and parts[0] == "song" and parts[1] in fake.fail_once:
                    fake.fail_once.discard(parts[1])
                    return self._send(503, "<html><body><h1>Something went wrong</h1></body></html>")
                if len(parts) == 2 and parts[0] == "song" and parts[1] in fake.songs:
                    song = fake.songs[parts[1]]
                    cfg = json.dumps({"id": parts[1], "title": song["title"], "delivery": fake.config["delivery"],
                                      "confirm": fake.config["confirm"], "prepare_ms": fake.config["prepare_ms"],
                                      "ui": fake.config["download_ui"], "aria": fake.config["box_aria"],
                                      "left": fake.config["downloads_left"], "unlocked": parts[1] in fake.counted,
                                      "stems": fake.stems.get(parts[1], "none"),
                                      "extract_confirm": fake.config["extract_confirm"],
                                      "stems_aria": fake.config["stems_aria"],
                                      "stems_load_ms": fake.config["stems_load_ms"],
                                      "extract_silent": fake.config["extract_silent"],
                                      "confirm_close_ms": fake.config["confirm_close_ms"],
                                      "files_start": fake.config["files_start"],
                                      "files_square": fake.config["files_square"],
                                      "credits_ui": fake.config["credits_ui"]})
                    similar = "".join(
                        f'<div class="row"><a href="/song/{s}">{html.escape(fake.songs[s]["title"])}</a>'
                        f'<button aria-label="More options">...</button></div>' for s in fake.similar)
                    artist = ("Bokin" if song["owner"] == "me" else "Dr. Someone Else") + (
                        "" if song["owner"] == "me" else ' <button class="follow">Follow</button>')
                    body = (SONG_BODY.replace("__TITLE__", html.escape(song["title"]))
                            .replace("__ARTIST__", artist).replace("__SIMILAR__", similar)
                            .replace("__MORE__", html.escape(fake.config["more_label"]))
                            .replace("__DISABLED__", "" if song["status"] == "complete" else 'aria-disabled="true"')
                            .replace("__STRAY__", fake.stray)
                            .replace("__LYRICS__", LYRICS_BODY.replace("__TEXT__", html.escape(song["lyrics"]))
                                     if song["lyrics"] else ""))
                    return self._page(body, SONG_SCRIPT.replace("__CFG__", cfg))
                return self._send(404, "not found")

            def do_POST(self):
                u = urlparse(self.path)
                q = parse_qs(u.query)
                parts = [p for p in u.path.split("/") if p]
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                if u.path == "/sign-in":
                    payload = json.dumps({"sub": fake.config["user_id"], "sid": secrets.token_hex(8)}).encode()
                    sid = ".".join(base64.urlsafe_b64encode(p).decode().rstrip("=") for p in
                                   (b'{"alg":"RS256"}', payload, secrets.token_bytes(16)))
                    fake.sessions.add(sid)
                    fake.signins += 1
                    return self._send(303, b"", headers=(
                        ("Set-Cookie", f"__session={sid}; Max-Age=31536000; Path=/"),
                        ("Set-Cookie", "__client_uat=1793000000; Max-Age=31536000; Path=/"), ("Location", "/")))
                if not self._signed_in():
                    return self._send(401, "signed out")
                if u.path == "/api/buy":
                    fake.buy_clicks += 1
                    return self._send(200, "{}", "application/json")
                if u.path == "/api/pressed":
                    fake.pressed.append(q.get("what", [""])[0])
                    return self._send(200, "{}", "application/json")
                if u.path == "/api/stems-open":
                    fake.stems_opened.append(q.get("id", [""])[0])
                    return self._send(200, "{}", "application/json")
                if len(parts) == 4 and parts[:2] == ["api", "stems"] and parts[2] in fake.songs:
                    sid, what = parts[2], parts[3]
                    if what == "extract":
                        if fake.config["credits"] == 0:
                            return self._send(200, json.dumps({"credits": False}), "application/json")
                        fake.extract_clicks.append(sid)
                        fake.stems[sid] = "extracting"

                        def done(sid=sid):
                            time.sleep(fake.config["extract_ms"] / 1000)
                            fake.stems[sid] = "ready"

                        threading.Thread(target=done, daemon=True).start()
                        return self._send(200, json.dumps({"ok": True}), "application/json")
                    if what == "download":
                        if fake.stems.get(sid) != "ready":
                            return self._send(409, "{}", "application/json")
                        fake.stems_downloads.append((sid, q.get("files", [""])[0], q.get("tempo", [""])[0]))
                        return self._send(200, json.dumps({"ok": True}), "application/json")
                if len(parts) == 3 and parts[:2] == ["api", "download"] and parts[2] in fake.songs:
                    sid, fmt = parts[2], q.get("fmt", [""])[0]
                    with fake.lock:
                        fake.picked.append((sid, fmt))
                        if sid not in fake.counted:
                            left = fake.config["downloads_left"]
                            if left is not None and left <= 0:
                                return self._send(200, json.dumps({"limit": True}), "application/json")
                            if left is not None:
                                fake.config["downloads_left"] = left - 1
                            fake.counted.append(sid)
                    return self._send(200, json.dumps({"ok": True}), "application/json")
                return self._send(404, "not found")

        return Handler


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Suno</title>
<style>
  body { font: 14px sans-serif; margin: 0; padding: 10px 10px 60px; }
  [hidden] { display: none !important; }
  button, [role=menuitem] { display: inline-block; border: 1px solid #555; padding: 4px 8px; margin: 2px;
    cursor: pointer; background: #fff; }
  [role=menu] { position: absolute; background: #fff; border: 1px solid #333; padding: 4px; z-index: 5; }
  [role=menuitem] { display: block; }
  [aria-disabled=true], button:disabled { opacity: .4; }
  [role=dialog] { position: fixed; top: 100px; left: 200px; width: 420px; background: #fff; border: 2px solid #333;
    padding: 16px; z-index: 10; }
  .player { position: fixed; left: 0; right: 0; bottom: 0; height: 40px; background: #eee; }
  .row { height: 56px; border-bottom: 1px solid #ddd; display: flex; align-items: center; gap: 8px; }
  #songs { height: 420px; overflow-y: auto; border: 1px solid #999; width: 700px; }
</style></head>
<body>
<script>
window.__CLERK__ = {loaded: false, user: null};
setTimeout(() => { window.__CLERK__.user = __USER__; window.__CLERK__.loaded = true; }, 300);
</script>
__BODY__
<script>__SCRIPT__</script>
</body></html>"""

SIGN_IN_BUTTON = '<button id="signin" onclick="location.href=\'/sign-in\'">Sign In</button>'

SIGNIN_PAGE = """<!doctype html><html lang="en"><body>
<h1>Sign in to Suno</h1><form method="post" action="/sign-in"><button>Continue with Google</button></form>
<script>setTimeout(() => document.forms[0].submit(), 300);</script>
</body></html>"""

WORKSPACE_BODY = """
<aside><a href="/create">Create</a> <a href="/me">Library</a></aside>
<h2>My Workspace</h2>
<div id="pager" hidden><button aria-label="Previous page" id="prevpage">&lsaquo;</button>
  <button aria-label="Next page" id="nextpage">&rsaquo;</button></div>
<div id="songs"><div id="spacer"></div><div id="rows"></div><button id="loadmore" hidden>Load more</button></div>
<div class="player">Now playing: <a href="/song/" id="stray">Bài đang phát</a></div>
"""

WORKSPACE_SCRIPT = """
const cfg = __CFG__;
const box = document.getElementById('songs'), rows = document.getElementById('rows');
const spacer = document.getElementById('spacer'), more = document.getElementById('loadmore');
document.getElementById('stray').href = '/song/' + cfg.stray;
let page = 0, hasMore = true, loading = false, dropped = 0;
const prev = document.getElementById('prevpage');
function load() {
  if (loading || !hasMore) return;
  loading = true;
  fetch(`/api/ws/${cfg.wid}?page=${page}`).then(r => r.json()).then(j => {
    if (cfg.paging === 'pages') {  // one page at a time, like suno.com's Create page
      rows.replaceChildren(); dropped = 0; spacer.style.height = '0px'; box.scrollTop = 0;
      prev.disabled = page === 0;
    }
    for (const s of j.songs) {
      const row = document.createElement('div'); row.className = 'row';
      const cover = document.createElement('a'); cover.href = '/song/' + s.id; cover.innerHTML = '<img alt="">';
      const title = document.createElement('a'); title.href = '/song/' + s.id; title.textContent = s.title;
      const tag = document.createElement('span'); tag.textContent = 'v5';
      const btn = document.createElement('button'); btn.setAttribute('aria-label', 'More options');
      btn.textContent = '...';
      row.append(cover, title, tag, btn); rows.append(row);
    }
    page += 1; hasMore = j.more; loading = false;
    more.hidden = !(cfg.paging === 'button' && hasMore);
    trim();
  });
}
function trim() {  // like a virtual list: rows far above the view are dropped, a spacer keeps the height
  while (rows.children.length > 20) {
    const first = rows.children[0];
    if (first.offsetTop + first.offsetHeight > box.scrollTop - 200) break;
    dropped += first.offsetHeight; first.remove(); spacer.style.height = dropped + 'px';
  }
}
box.addEventListener('scroll', () => {
  trim();
  if (cfg.paging === 'scroll' && box.scrollTop + box.clientHeight > box.scrollHeight - 100) setTimeout(load, 300);
});
more.addEventListener('click', load);
// Next page stays enabled on the last page, where it does nothing (as on suno.com)
document.getElementById('pager').hidden = cfg.paging !== 'pages';
document.getElementById('nextpage').addEventListener('click', load);
prev.addEventListener('click', () => { if (page > 1) { page -= 2; hasMore = true; load(); } });
setTimeout(load, 400);
"""

SONG_BODY = """
<div class="cover"><img alt=""> <button aria-label="Download cover image" data-never="cover">&#8615;</button></div>
<h1>__TITLE__</h1>
<div class="artist">__ARTIST__</div>
<div><button aria-label="Like">Like</button> <button aria-label="__MORE__" id="more">...</button></div>
<div role="menu" id="menu" hidden>
  <div role="menuitem">Remix</div>
  <div role="menuitem">Edit</div>
  <div role="menuitem">Publish</div>
  <div role="menuitem">Share</div>
  <div role="menuitem" id="dl" __DISABLED__>Download</div>
  <div role="menuitem">Manage</div>
  <div role="menuitem">Add to Queue</div>
  <div role="menuitem">Add to Playlist</div>
  <div role="menuitem">Song Radio</div>
  <div role="menuitem">Report</div>
  <div role="menuitem" data-never="trash">Move to Trash</div>
</div>
<div role="menu" id="sub" hidden style="margin-left: 160px">
  <div role="menuitem" data-fmt="mp3">MP3 Audio</div>
  <div role="menuitem" data-fmt="wav">WAV Audio</div>
  <div role="menuitem" data-fmt="video">Video</div>
</div>
<div role="dialog" id="dlg" hidden></div>
<div role="dialog" id="stemsdlg" hidden style="top: 60px; left: 120px; width: 560px"></div>
<div role="dialog" id="filesdlg" hidden style="top: 120px; left: 240px"></div>
<div role="alertdialog" id="askdlg" hidden style="top: 200px; left: 300px; width: 320px"></div>
__LYRICS__
<aside id="similar" style="position: absolute; top: 10px; left: 760px; width: 300px; height: 360px; overflow-y: auto;
  border: 1px solid #999"><b>Similar</b>__SIMILAR__</aside>
<section><h3>Comments</h3><div>Nice! <button aria-label="More options">...</button></div></section>
<div class="player">Now playing: <a href="/song/__STRAY__">Bài đang phát</a></div>
"""

LYRICS_BODY = """<section><h3>Lyrics</h3><p class="whitespace-pre-wrap" style="white-space: pre-wrap">__TEXT__</p>
</section>"""

SONG_SCRIPT = """
const cfg = __CFG__;
const $ = (s) => document.querySelector(s);
const menu = $('#menu'), sub = $('#sub'), dl = $('#dl'), dlg = $('#dlg');
$('#more').addEventListener('click', () => { menu.hidden = !menu.hidden; sub.hidden = true; });
const openSub = () => { if (cfg.ui === 'menu' && dl.getAttribute('aria-disabled') !== 'true') sub.hidden = false; };
dl.addEventListener('mouseenter', openSub);
dl.addEventListener('click', () => (cfg.ui === 'box' ? openBox() : openSub()));
function el(tag, text) { const e = document.createElement(tag); if (text != null) e.textContent = text; return e; }
const ICON = '<svg width="12" height="12" aria-hidden="true"><path d="M1 6l3 3 7-7"/></svg>';
for (const b of document.querySelectorAll('[data-never]')) b.addEventListener('click', () => {
  fetch('/api/pressed?what=' + b.dataset.never, {method: 'POST'});
});
function openBox() {  // suno.com, October 2026: the download box
  if (dl.getAttribute('aria-disabled') === 'true') return;
  menu.hidden = sub.hidden = true;
  const chosen = new Set(['mp3']);  // several rows can be chosen; every chosen format is downloaded
  const close = el('button'); close.setAttribute('aria-label', 'Close'); close.innerHTML = ICON;
  close.onclick = () => { dlg.hidden = true; };
  const rows = [['m4a', 'M4A'], ['mp3', 'MP3'], ['wav', 'WAV'], ['video', 'MP4 video asset']].map(([f, label]) => {
    const b = el('button'); b.append(el('span', label)); b.className = 'fmt'; b.dataset.f = f;
    b.onclick = () => { if (!chosen.delete(f)) chosen.add(f); paint(); };
    return b;
  });
  const manage = el('button'); manage.innerHTML = ICON + '<span>Manage</span>';  // (its own icon)
  manage.onclick = () => { openStems(); setTimeout(() => dlg.remove(), 600); };  // (the box goes, as a portal does)
  const stems = el('div'); stems.append(el('span', 'Stems & MIDI'), manage);
  function paint() {  // the check mark on a chosen row is all that tells (no aria- attribute, as on suno.com)
    for (const b of rows) {
      const on = chosen.has(b.dataset.f);
      b.style.background = on ? '#eee8d5' : '';
      const mark = b.querySelector('svg'); if (mark) mark.remove();
      if (on) b.insertAdjacentHTML('beforeend', ICON);
      if (cfg.aria) b.setAttribute('aria-pressed', String(on));
    }
  }
  const go = el('button', cfg.unlocked ? 'Download' : 'Unlock & Download');
  const plan = el('div');
  if (cfg.unlocked) {
    plan.append(el('span', "You've unlocked this song. You can return and download at any time. "));
    const more = el('a', 'Learn more.'); more.href = '/blog/suno-updates-tos'; plan.append(more);
  } else {
    plan.append(el('span', 'Plan'), el('b', 'Premier'), el('span', 'Downloads'),
                el('b', cfg.left == null ? 'Unlimited' : String(cfg.left)), el('span', 'Refreshes'), el('b', '11/28/26'));
  }
  go.onclick = () => {
    const fmts = ['mp3', 'wav'].filter(f => chosen.has(f));
    if (!fmts.length) return;
    go.disabled = true; go.textContent = 'Preparing...';
    Promise.all(fmts.map(f => fetch(`/api/download/${cfg.id}?fmt=${f}`, {method: 'POST'}).then(r => r.json())))
      .then(answers => {
        if (answers.some(j => j.limit)) { limitBox(); return; }
        fmts.forEach((f, i) => setTimeout(() => deliver(f), cfg.prepare_ms + i * 300));
      });
  };
  if (!dlg.isConnected) document.body.insertBefore(dlg, $('#stemsdlg'));
  dlg.replaceChildren(close, el('h2', `Download '${cfg.title}'`), ...rows, stems, go, plan);
  paint();
  dlg.hidden = false;
}
function limitBox() {
  box(`<h2>You've reached your download limit</h2><p>Your plan's downloads for this month are used up.</p>
       <button id="buy">Buy more downloads</button> <button onclick="dlg.hidden = true">Close</button>`);
  $('#buy').addEventListener('click', () => fetch('/api/buy', {method: 'POST'}));
}
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    menu.hidden = sub.hidden = true; dlg.hidden = true;
    for (const d of ['#stemsdlg', '#filesdlg', '#askdlg']) $(d).hidden = true;
  }
});
// Stems & MIDI (the owner's screenshots, October 2026): Manage → "Extract Stems and MIDI" (Auto split, Extract, the
// stems made so far, each with its own Download icon that must not be pressed, and a Download ▾ button) → "Download":
// MP3, WAV, MIDI ticked (a check mark only, unless cfg.stems_aria), Tempo behavior, Cancel / Download → one zip.
const CARET = '<svg width="10" height="10" aria-hidden="true"><path d="M1 3l4 4 4-4"/></svg>';
function openStems() {
  fetch('/api/stems-open?id=' + cfg.id, {method: 'POST'});
  const box = $('#stemsdlg');
  let state = cfg.stems_load_ms ? 'loading' : cfg.stems;  // (loading: nothing shown yet)
  const close = el('button'); close.setAttribute('aria-label', 'Close'); close.innerHTML = ICON;
  close.onclick = () => { box.hidden = true; };
  const tabs = ['Auto split', 'Split from mix', 'Advanced split'].map((t, i) => {
    const b = el('button', t); if (i === 2) b.append(el('span', ' New')); return b;
  });
  const extract = el('button', 'Extract');
  const list = el('div');
  const dl = el('button'); dl.innerHTML = '<span>Download</span>' + CARET;
  function render() {
    list.replaceChildren();
    if (state === 'ready') {
      for (const n of ['Drums', 'Bass', 'Guitar', 'Piano', 'Vocals', 'Other']) {
        const one = el('button'); one.setAttribute('aria-label', 'Download'); one.innerHTML = ICON;
        one.onclick = () => fetch('/api/pressed?what=one-stem', {method: 'POST'});
        const row = el('div'); row.append(el('span', n), one); list.append(row);
      }
    } else if (state === 'extracting' && !cfg.extract_silent) list.append(el('p', 'Extracting stems...'));
    dl.hidden = state !== 'ready';
  }
  function poll() {
    setTimeout(() => fetch('/api/stems/' + cfg.id).then(r => r.json()).then(j => {
      state = j.state; render(); if (state === 'extracting') poll();
    }), 300);
  }
  function start() {
    fetch(`/api/stems/${cfg.id}/extract`, {method: 'POST'}).then(r => r.json()).then(j => {
      if (j.credits === false && cfg.credits_ui === 'toast') {
        const t = el('div'); t.setAttribute('role', 'status'); t.className = 'toast';
        t.textContent = "You don't have enough credits to extract stems.";
        document.body.append(t);
        return;
      }
      if (j.credits === false) {
        const ask = $('#askdlg'), up = el('button', 'Upgrade'), no = el('button', 'Close');
        up.onclick = () => fetch('/api/pressed?what=upgrade', {method: 'POST'});
        no.onclick = () => { ask.hidden = true; };
        ask.replaceChildren(el('h2', 'Not enough credits'), el('p', 'Get more credits to extract stems.'), up, no);
        ask.hidden = false;
        return;
      }
      state = 'extracting'; render(); poll();
    });
  }
  extract.onclick = () => {
    if (!cfg.extract_confirm) return start();
    const ask = $('#askdlg'), yes = el('button', 'Extract'), no = el('button', 'Cancel');
    yes.onclick = () => { start(); setTimeout(() => { ask.hidden = true; }, cfg.confirm_close_ms); };
    no.onclick = () => { ask.hidden = true; };
    ask.replaceChildren(el('h2', 'Extract Stems and MIDI?'), el('p', `Auto split for '${cfg.title}' uses 10 credits.`),
                        no, yes);
    ask.hidden = false;
  };
  dl.onclick = openFiles;
  box.replaceChildren(close, el('h2', 'Extract Stems and MIDI'), el('b', cfg.title), ...tabs,
                      el('p', 'Auto extract from a list of 12 instruments.'), extract, list, dl);
  render();
  if (state === 'extracting') poll();
  if (cfg.stems_load_ms) fetch(`/api/stems/${cfg.id}?wait=${cfg.stems_load_ms}`).then(r => r.json()).then(j => {
    state = j.state; render(); if (state === 'extracting') poll();
  });
  box.hidden = false;
}
function openFiles() {
  const box = $('#filesdlg');
  const ticked = new Set(cfg.files_start.split(',').filter(Boolean));
  let tempo = 'follow';
  const files = [['mp3', 'MP3'], ['wav', 'WAV'], ['midi', 'MIDI']].map(([f, label]) => {
    const mark = el('span'); mark.className = 'tick';
    const row = el('div'); row.append(mark, el('span', label));
    if (f === 'midi') row.append(el('span', ' May take longer to process'));
    row.onclick = () => { if (!ticked.delete(f)) ticked.add(f); paint(); };
    row.dataset.f = f;
    return row;
  });
  const tempos = [['fixed', 'Fixed tempo', 'Uses one steady average BPM'], ['follow', 'Follow tempo changes',
    'Keeps every tempo shift']].map(([t, name, what]) => {
    const row = el('div'); row.append(el('b', name), el('span', ' ' + what)); row.dataset.t = t;
    row.onclick = () => { tempo = t; paint(); };
    return row;
  });
  function paint() {
    for (const row of files) {
      const mark = row.firstChild, on = ticked.has(row.dataset.f);
      const check = on ? '<path d="M3 6l2 2 4-4"/>' : '';  // (files_square: an svg square either way)
      mark.innerHTML = cfg.files_square ? `<svg width="12" height="12"><rect width="10" height="10"/>${check}</svg>`
        : (on ? ICON : '');
      if (cfg.stems_aria) { mark.setAttribute('role', 'checkbox'); mark.setAttribute('aria-checked', String(on)); }
    }
    for (const row of tempos) {
      const old = row.querySelector('svg'); if (old) old.remove();
      if (row.dataset.t === tempo) row.insertAdjacentHTML('beforeend', ICON);
    }
  }
  const cancel = el('button', 'Cancel'), go = el('button', 'Download');
  cancel.onclick = () => { box.hidden = true; };
  go.onclick = () => {
    const chosen = ['wav', 'mp3', 'midi'].filter(f => ticked.has(f));
    if (!chosen.length) return;
    fetch(`/api/stems/${cfg.id}/download?files=${chosen}&tempo=${tempo}`, {method: 'POST'})
      .then(() => fetch(`/stemszip/${cfg.id}.zip?files=${chosen}`)).then(r => r.blob()).then(b => {
        const a = document.createElement('a'); a.href = URL.createObjectURL(b);
        a.download = cfg.title + ' - Auto split.zip'; document.body.append(a); a.click();
      });
    box.hidden = true;
  };
  box.replaceChildren(el('h2', 'Download'), el('p', 'Auto split · 6 stems'), el('p', 'Select files to download'),
                      ...files, el('p', 'Tempo behavior'), ...tempos, cancel, go);
  paint();
  box.hidden = false;
}
function box(inner) { dlg.innerHTML = inner; dlg.hidden = false; }
function deliver(fmt) {
  const url = `/files/${cfg.id}.${fmt}`;
  if (cfg.delivery === 'newtab') { window.open(`/cdn/${cfg.id}.${fmt}`, '_blank'); }
  else if (cfg.delivery === 'attach') {
    const a = document.createElement('a'); a.href = url; document.body.append(a); a.click();
  }
  else fetch(url).then(r => r.blob()).then(b => {
    const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = cfg.title + '.' + fmt;
    document.body.append(a); a.click();
  });
  dlg.hidden = true;
}
for (const item of sub.querySelectorAll('[data-fmt]')) item.addEventListener('click', () => {
  const fmt = item.dataset.fmt;
  menu.hidden = sub.hidden = true;
  if (fmt === 'video') return;
  fetch(`/api/download/${cfg.id}?fmt=${fmt}`, {method: 'POST'}).then(r => r.json()).then(j => {
    if (j.limit) { limitBox(); return; }
    if (fmt === 'wav') {
      box(`<h2>Download WAV Audio</h2><p id="state">Preparing your file...</p>
           <button onclick="dlg.hidden = true">Cancel</button> <button id="go" disabled>Download File</button>`);
      setTimeout(() => { $('#state').textContent = 'Your file is ready'; $('#go').disabled = false; }, cfg.prepare_ms);
      $('#go').addEventListener('click', () => deliver('wav'));
    } else if (cfg.confirm) {
      box(`<h2>Download MP3 Audio</h2><p>This uses 1 of your downloads.</p>
           <button onclick="dlg.hidden = true">Cancel</button> <button id="go">Download</button>`);
      $('#go').addEventListener('click', () => deliver('mp3'));
    } else deliver('mp3');
  });
});
"""
