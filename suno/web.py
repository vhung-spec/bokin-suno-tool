"""suno.com, driven in a real Chrome: sign in once, read the songs of a workspace, download each song.

No Suno API: the program does what a person does on suno.com. It opens the workspace (or playlist) link, reads the
song links in its list while scrolling (and through Next page, which suno.com leaves enabled on the last page), then
for each song opens the song's page, reads the lyrics it shows, and presses More options → Download. suno.com (October
2026, tried on the owner's computer) then opens a box "Download '<title>'" listing M4A, MP3, WAV, MP4 video asset,
Stems & MIDI, with the plan's downloads left ("Downloads 59") and an "Unlock & Download" button ("Download" for a song
downloaded before). Several rows can be chosen at once (MP3 is, at first) and a check mark shows which: the program
chooses WAV (or MP3), unchooses every other row, and presses that button. The older menu (Download → WAV Audio, then a
box with Download File) works too. The program keeps the file Chrome receives.

Stems & MIDI (download_stems): in that box, Stems & MIDI → Manage opens "Extract Stems and MIDI"; on Auto split, a song
whose stems are not made yet gets Extract pressed (the owner's choice, October 2026: it may use Suno credits; a box
offering to buy or upgrade is never pressed and stops the run), then Download → a box "Select files to download" (MP3,
WAV, MIDI ticked as asked; Tempo behavior: Follow tempo changes or Fixed tempo) → Download. The files Chrome receives
(a zip, most likely) are returned to the caller. Downloads go
through Suno's own Download button, so Suno counts them exactly as when a person downloads by hand; when Suno says
the plan's downloads are used up, the run stops. The program never presses a Buy/Upgrade button and never takes the
audio any other way. Every selector and button text is in SEL. BOKIN_SUNO_URL points the program at a stand-in Suno
(tests/fake_suno.py).
"""
import base64
import json
import os
import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse

BASE = os.environ.get("BOKIN_SUNO_URL", "https://suno.com").rstrip("/")

SEL = {
    "song_link": 'a[href*="/song/"]',
    "sign_in": 'button:text-matches("^(sign in|log in|sign up)$", "i"), a:text-matches("^(sign in|log in)$", "i")',
    "next_page": 'button[aria-label="Next page" i], button:text-matches("^(load more|show more)$", "i")',
    "more": 'button[aria-label="More Options" i], button[aria-label="More options" i], '
            'button[aria-label="More actions" i], button[aria-label="More" i]',
    "menu_item": '[role="menuitem"], [role="menu"] button, [data-radix-popper-content-wrapper] button, '
                 '[data-radix-popper-content-wrapper] [role="button"]',
    "dialog": '[role="dialog"], [role="alertdialog"], [aria-modal="true"]',
    # the rows of the download box's list of formats (M4A, MP3, WAV, MP4 video asset, Stems & MIDI)
    "dialog_option": 'button, [role="radio"], [role="option"], [role="menuitemradio"], [role="checkbox"], label, li',
    # the check mark a chosen row of the download box shows (suno.com, October 2026: the row's only icon; the rows
    # carry no aria-checked / aria-pressed)
    "dialog_check": "svg",
    "dialog_button": 'button, a[href], [role="button"]',
    "song_title": "h1",
    # the lyrics on a song page: these first, else the longest multi-line text shown with its line breaks kept
    # (white-space: pre*), outside menus, boxes, links and buttons (JS_LYRICS)
    "lyrics": '[data-testid*="lyrics" i]',
    # button and box texts (English UI)
    "text_download": re.compile(r"^download\b", re.I),
    "text_format": {"wav": re.compile(r"\bwav\b", re.I), "mp3": re.compile(r"\bmp3\b", re.I)},
    # a row of the download box: exactly the format's name (not "MP4 video asset", "M4A")
    "text_dialog_format": {"wav": re.compile(r"^wav( audio)?$", re.I), "mp3": re.compile(r"^mp3( audio)?$", re.I)},
    # any format row of the download box: several can be chosen at once (MP3 at first), and every chosen row is
    # downloaded, so all but the wanted one are unchosen ("Close", "Manage", "Download" are not rows)
    "text_dialog_row": re.compile(r"^(m4a|mp3|wav|flac|aac|ogg|mp4|video|stems|midi)\b", re.I),
    "text_go": re.compile(r"^(download( file| wav| mp3| audio| song)?|unlock\s*(&|and)\s*download|continue|confirm)$",
                          re.I),
    # the download box's count of the plan's downloads left, at 0: nothing is pressed (its words may run together:
    # "PremierDownloads0Refreshes")
    "text_none_left": re.compile(r"downloads\s*:?\s*0(?![\d.,/])", re.I),
    "text_buy": re.compile(r"\b(buy|purchase|upgrade|subscribe|payment|checkout)\b|[$€£₫]\s?\d", re.I),
    # a song page with a Follow button is someone else's song (suno.com shows none on the account's own songs):
    # never downloaded, it would use up one of the plan's downloads for nothing
    "text_follow": re.compile(r"^(follow|following|unfollow)$", re.I),
    # Stems & MIDI (download_stems)
    # (the box's words may run together: "Stems & MIDIManage")
    "text_stems_row": re.compile(r"stems\s*(&|and)\s*midi", re.I),
    "text_manage": re.compile(r"^manage$", re.I),
    "text_stems_box": re.compile(r"extract\s+stems", re.I),  # the "Extract Stems and MIDI" box
    "text_auto_split": re.compile(r"^auto\s*split$", re.I),
    "text_extract": re.compile(r"^extract$", re.I),
    "text_confirm": re.compile(r"^(extract|confirm|continue|ok|yes)$", re.I),  # a box confirming the extraction
    "text_plain_download": re.compile(r"^download$", re.I),
    "text_files_box": re.compile(r"select files|tempo behaviou?r", re.I),  # the stems' "Download" box
    "text_stem_file": {"mp3": re.compile(r"^mp3$", re.I), "wav": re.compile(r"^wav$", re.I),
                       "midi": re.compile(r"^midi\b", re.I)},
    "text_tempo": {"follow": re.compile(r"^follow tempo", re.I), "fixed": re.compile(r"^fixed tempo", re.I)},
    "text_no_credits": re.compile(r"\b(not enough|out of|insufficient|no)\s+credits?\b|\bget\s+(more\s+)?credits\b",
                                  re.I),
    "stem_option": 'button, [role="checkbox"], [role="radio"], [role="option"], [role="tab"], label, li, span, p, div',
    "text_limit": re.compile(r"\b(limit|out of downloads|no downloads|0 downloads|downloads? (left|remaining))\b", re.I),
}

SONG_ID_RE = re.compile(r"/song/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I)
AUDIO_URL_RE = re.compile(r"\.(wav|mp3)$", re.I)

# window.Clerk is Suno's sign-in library: 'in:<user id>', 'out', 'loading' or 'none' (not on the page). It lives in
# the page's own JavaScript world, so it is read with isolated_context=False (patchright reads in a separate world).
# A page may not show it (suno.com did not, on the owner's computer): Clerk's own cookies say it too (cookie_state).
JS_STATE = """() => { const c = window.Clerk; if (!c) return 'none'; if (!c.loaded) return 'loading';
  return c.user ? 'in:' + (c.user.id || '') : 'out'; }"""

# One pass over the song list: the songs it shows now, then a scroll. The list is the scrollable box holding most
# song links (marked so later passes use the same box); links in fixed or sticky bars (the player) are not songs of
# the list.
JS_COLLECT = r"""(sel) => {
  const ID = /\/song\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i;
  const pinned = (el) => { for (let p = el; p && p !== document.body; p = p.parentElement) {
    const pos = getComputedStyle(p).position; if (pos === 'fixed' || pos === 'sticky') return true; } return false; };
  const scrollable = (el) => /(auto|scroll|overlay)/.test(getComputedStyle(el).overflowY)
    && el.scrollHeight > el.clientHeight + 4;
  const links = [...document.querySelectorAll(sel)].filter(a => ID.test(a.getAttribute('href') || '') && !pinned(a));
  let box = document.querySelector('[data-bokin-list]');
  if (!box || !box.isConnected) {
    const counts = new Map();
    for (const a of links) {
      let p = a.parentElement;
      while (p && p !== document.body && !scrollable(p)) p = p.parentElement;
      const b = (p && p !== document.body) ? p : document.scrollingElement;
      counts.set(b, (counts.get(b) || 0) + 1);
    }
    let best = 0; box = null;
    for (const [b, n] of counts) if (n > best) { box = b; best = n; }
    if (box && box !== document.scrollingElement) box.setAttribute('data-bokin-list', '1');
  }
  if (!box) return {songs: [], bottom: true, height: 0};
  const songs = [];
  for (const a of links) {
    if (box !== document.scrollingElement && !box.contains(a)) continue;
    const text = ((a.innerText || '').trim().split('\n')[0] || a.getAttribute('title') || '').trim();
    songs.push([a.getAttribute('href').match(ID)[1].toLowerCase(), text]);
  }
  const before = box.scrollTop;
  box.scrollTop = before + Math.max(200, box.clientHeight * 0.8);
  const bottom = box.scrollTop + box.clientHeight >= box.scrollHeight - 4;
  return {songs, bottom, height: box.scrollHeight};
}"""

# The song links the list shows now (to tell whether Next page / Load more changed it)
JS_SHOWN = r"""(sel) => { const box = document.querySelector('[data-bokin-list]') || document;
  return [...box.querySelectorAll(sel)].map(a => a.getAttribute('href')).join('|'); }"""


# The lyrics a song page shows, as plain text ("" for none: an instrumental, or a page laid out otherwise)
JS_LYRICS = r"""(sel) => {
  const away = 'nav, header, footer, aside, a, button, textarea, input, [role="dialog"], [role="alertdialog"], '
    + '[role="menu"], [contenteditable="true"]';
  const shown = (el) => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== 'hidden';
  const text = (el) => (el.innerText || '').replace(/\r/g, '').replace(/\n{3,}/g, '\n\n').trim();
  for (const el of document.querySelectorAll(sel)) if (shown(el) && text(el)) return text(el).slice(0, 20000);
  let best = '';
  for (const el of document.querySelectorAll('p, div, span, pre, section')) {
    if (!shown(el) || el.closest(away) || !/^pre/.test(getComputedStyle(el).whiteSpace)) continue;
    const t = text(el);
    if (t.includes('\n') && t.length > best.length) best = t;
  }
  return best.slice(0, 20000);
}"""


class SunoError(Exception):
    """A step on suno.com failed. code: not_signed_in, wrong_account, no_songs, not_ready, limit, stuck, not_mine
    (someone else's song: skipped, nothing pressed)."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@dataclass
class Song:
    id: str
    title: str

    @property
    def link(self):
        return f"{BASE}/song/{self.id}"


# ---- links ----

def check_link(text):
    """A workspace, playlist or song link on suno.com -> the full URL. Raises ValueError (the reason, in Vietnamese)."""
    text = (text or "").strip().strip('"').strip("'")
    if text and "://" not in text:
        text = "https://" + text
    u = urlparse(text)
    allowed = {urlparse(BASE).netloc.lower()}
    if urlparse(BASE).netloc.lower() == "suno.com":
        allowed.add("www.suno.com")
    if u.scheme not in ("http", "https") or u.netloc.lower() not in allowed:
        raise ValueError(f"'{text}' không phải link của Suno. Mở workspace trên suno.com rồi chép link trên thanh "
                         "địa chỉ (dạng https://suno.com/...)")
    if u.path.strip("/") == "":
        raise ValueError("Link chỉ là trang chủ Suno. Mở đúng workspace rồi chép link trên thanh địa chỉ")
    return text


def song_id_of(url):
    m = SONG_ID_RE.search(urlparse(url).path)
    return m.group(1).lower() if m else None


# ---- small page helpers ----

def _visible(locator):
    try:
        return locator.is_visible()
    except Exception:
        return False


def _enabled(locator):
    try:
        return (locator.is_visible() and locator.is_enabled() and locator.get_attribute("aria-disabled") != "true"
                and locator.get_attribute("data-disabled") is None)
    except Exception:
        return False


def _text(locator):
    try:
        return re.sub(r"\s+", " ", locator.inner_text()).strip()
    except Exception:
        return ""


def _find_text(page, selector, pattern):
    """The first visible element of `selector` whose text (or aria-label) matches `pattern`, or None."""
    for loc in page.locator(selector).all():
        if not _visible(loc):
            continue
        text = _text(loc)
        if not text:
            try:
                text = loc.get_attribute("aria-label") or ""
            except Exception:
                text = ""
        if pattern.search(text):
            return loc
    return None


def _poll(page, find, timeout_ms, step_ms=100):
    """find() again and again until it returns something or the time is up: no fixed waits."""
    end = time.monotonic() + timeout_ms / 1000
    while True:
        found = find()
        if found or time.monotonic() >= end:
            return found
        page.wait_for_timeout(step_ms)


def _jwt_subject(token):
    """The "sub" (Clerk's user id) of a session token, read without checking it: only to tell accounts apart."""
    try:
        part = token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
        sub = payload.get("sub")
        return sub if isinstance(sub, str) and sub else None
    except (IndexError, ValueError, AttributeError, TypeError):
        return None


def cookie_state(context):
    """Clerk's cookies on suno.com: __client_uat is the time of the last sign-in ("0" once signed out), __session the
    session's token (its "sub" is the user id). ('in', user id or None), ('out', None), or (None, None): no such
    cookie. Names may carry a suffix (__client_uat_xxxx)."""
    try:
        cookies = context.cookies(BASE + "/")
    except Exception:
        return None, None

    def named(c, name):
        return c.get("name") == name or str(c.get("name", "")).startswith(name + "_")

    uat = [str(c.get("value", "")).strip() for c in cookies if named(c, "__client_uat")]
    if not uat:
        return None, None
    if all(v in ("", "0") for v in uat):
        return "out", None
    user = None
    for c in cookies:
        if named(c, "__session"):
            user = _jwt_subject(str(c.get("value", ""))) or user
    return "in", user


def _signed_out_url(url):
    return bool(re.search(r"/(sign-?in|log-?in|sign-?up)\b|accounts\.", url, re.I))


def page_state(page, wait_seconds=25):
    """('in', user id or None) or ('out', None) for the page as it is now (waits for the sign-in library)."""
    start = time.monotonic()
    while True:
        if _signed_out_url(page.url):
            return "out", None
        try:
            s = page.evaluate(JS_STATE, isolated_context=False)
        except Exception:
            s = "loading"  # the page is still navigating
        if s.startswith("in:"):
            return "in", s[3:] or cookie_state(page.context)[1]
        if s == "out":
            return "out", None
        waited = time.monotonic() - start
        if (s == "none" and waited > 4) or waited > wait_seconds:
            # no sign-in library to ask on the page: Clerk's cookies, and a Sign in button means signed out
            if _visible(page.locator(SEL["sign_in"]).first):
                return "out", None
            state, user = cookie_state(page.context)
            if state or waited > wait_seconds or waited > 8:
                return ("in", user) if state != "out" else ("out", None)
        page.wait_for_timeout(500)


# ---- sign-in ----

def signed_in_user(page):
    """Opens suno.com; ('in', user id or None) or ('out', None)."""
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=90_000)
    return page_state(page)


def ensure_account(page, user_id):
    state, got = signed_in_user(page)
    if state != "in":
        raise SunoError("not_signed_in", "Tài khoản Suno chưa đăng nhập hoặc đã bị đăng xuất. Chạy lại: suno login <tên>")
    if user_id and got and got != user_id:
        raise SunoError("wrong_account", "Chrome đang đăng nhập một tài khoản Suno khác tài khoản đã lưu. "
                                         "Chạy lại: suno login <tên>")
    return got


def wait_for_login(context, log, settle_seconds=None, limit_minutes=30):
    """Opens suno.com in a visible window and waits while the person signs in and closes the window. Returns
    (signed_in, user id or None) as last seen. settle_seconds (tests) stops on its own once signed in that long."""
    closed = []
    context.on("close", lambda *_: closed.append(True))
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(BASE + "/", wait_until="domcontentloaded", timeout=90_000)
    host = urlparse(BASE).netloc.lower()
    signed_in, user, seen_at = False, None, 0.0
    seen = None
    deadline = time.monotonic() + limit_minutes * 60
    while not closed and time.monotonic() < deadline:
        try:
            pages = list(context.pages)
        except Exception:
            break
        if not pages:
            break
        page_says = None  # what Suno's own pages say: 'in:<id>', 'out', or None (no page could tell)
        where = [urlparse(p.url).netloc + urlparse(p.url).path for p in pages]
        for p in pages:
            if urlparse(p.url).netloc.lower() not in (host, "www." + host):
                continue
            try:
                s = p.evaluate(JS_STATE, isolated_context=False)
            except Exception:
                continue
            if s.startswith("in:") or (s == "out" and page_says is None):
                page_says = s
        cookies = cookie_state(context)
        if (page_says, cookies[0], where) != seen:
            seen = (page_says, cookies[0], where)
            log.debug("sign-in: pages %s, Clerk on the page %s, Clerk's cookies %s", where, page_says, cookies[0])
        if page_says and page_says.startswith("in:"):
            now_in, now_user = True, page_says[3:] or cookies[1]
        elif page_says == "out":
            now_in, now_user = False, None
        else:
            now_in, now_user = cookies[0] == "in", cookies[1]
        if now_in and (not signed_in or now_user != user):
            signed_in, user, seen_at = True, now_user, time.monotonic()
            log.info("Đã thấy đăng nhập Suno. Giờ đóng cửa sổ Chrome.")
        elif not now_in and signed_in and (page_says == "out" or cookies[0] == "out"):
            signed_in, user = False, None
        if settle_seconds and signed_in and time.monotonic() - seen_at >= settle_seconds:
            break
        try:
            context.wait_for_event("close", timeout=1000)
        except Exception:
            pass
    if not signed_in and seen:
        log.info("Lần cuối thấy: trang %s, Clerk trên trang: %s, cookie đăng nhập: %s", ", ".join(seen[2]) or "-",
                 seen[0] or "không có", seen[1] or "không có")
    return signed_in, user


# ---- the songs of a workspace ----

def _share_link(url):
    """suno.com/s/<code>: a share link, which Suno turns into a song's (or a playlist's) own address."""
    return bool(re.match(r"/s/[^/]+/?$", urlparse(url).path))


def list_songs(page, url, log, known=None, known_in_a_row=None, limit_minutes=20):
    """The songs shown at `url` (a workspace, playlist or song link, or a share link to one), in the order shown.
    A link that opens one song's page gives that song alone: the other song links on such a page (Similar, the
    artist's other songs) are other people's songs. With known(id) and known_in_a_row, reading stops once that many
    songs in a row are known: Suno lists the newest songs first, so a second run reads only the top of a large
    workspace."""
    page.goto(url, wait_until="domcontentloaded", timeout=90_000)
    if _share_link(url):  # Suno sends a share link on to the song's page, at once or from the page's script
        end = time.monotonic() + 30
        while _share_link(page.url) and time.monotonic() < end:
            page.wait_for_timeout(300)
        if _share_link(page.url):
            raise SunoError("no_songs", "Link chia sẻ này không mở ra bài hay playlist nào. Mở workspace trên suno.com "
                                        "rồi chép link trên thanh địa chỉ (dạng https://suno.com/create?wid=...)")
        log.info("Link chia sẻ dẫn tới: %s", urlparse(page.url).path)
    if page_state(page)[0] != "in":
        raise SunoError("not_signed_in", "Tài khoản Suno chưa đăng nhập hoặc đã bị đăng xuất. Chạy lại: suno login <tên>")
    one = song_id_of(page.url) or song_id_of(url)
    if one:
        if _share_link(url) or not song_id_of(url):
            log.info("Link này là link của một bài (không phải workspace): chỉ tải đúng bài đó")
        return [Song(one, "")]
    try:
        page.locator(SEL["song_link"]).first.wait_for(state="attached", timeout=30_000)
    except Exception:
        raise SunoError("no_songs", "Không thấy bài nào ở link này. Kiểm tra link (mở link trong Chrome thường xem có "
                                    "đúng workspace không); workspace trống thì không có gì để tải")
    page.wait_for_timeout(1000)
    songs = {}
    quiet, last_height, last_logged, streak = 0, -1, 0, 0
    deadline = time.monotonic() + limit_minutes * 60
    while time.monotonic() < deadline:
        r = page.evaluate(JS_COLLECT, SEL["song_link"])
        new = 0
        for sid, text in r["songs"]:
            if sid not in songs:
                songs[sid] = text
                new += 1
                streak = streak + 1 if known and known(sid) else 0
                if known_in_a_row and streak >= known_in_a_row:
                    break
            elif len(text) > len(songs[sid]):
                songs[sid] = text
        if known_in_a_row and streak >= known_in_a_row:
            log.info("Đọc tới bài thứ %d thì gặp %d bài liền đã tải từ trước: dừng đọc danh sách (các bài phía dưới "
                     "đã tải rồi; muốn đọc hết thì thêm --full)", len(songs), streak)
            break
        if len(songs) >= last_logged + 50:
            last_logged = len(songs) - len(songs) % 50
            log.info("Đã đọc %d bài...", len(songs))
        if new or r["height"] != last_height:
            quiet, last_height = 0, r["height"]
        elif r["bottom"]:
            quiet += 1
        if quiet >= 3:  # at the end and nothing new after three looks: the next page, if there is one
            more = next((b for b in page.locator(SEL["next_page"]).all() if _enabled(b)), None)
            if more is None:
                break
            shown = page.evaluate(JS_SHOWN, SEL["song_link"])
            more.click()
            # suno.com's Create page keeps Next page enabled on its last page, where a click changes nothing
            if not _poll(page, lambda: page.evaluate(JS_SHOWN, SEL["song_link"]) != shown, 10_000, 250):
                log.debug("Next page changed nothing: the end of the list")
                break
            page.evaluate("() => { const b = document.querySelector('[data-bokin-list]') || document.scrollingElement; "
                          "b.scrollTop = 0; }")
            quiet = 0
        page.wait_for_timeout(350 if new and not r["bottom"] else 700)  # quicker while songs keep coming
    else:
        log.warning("Đọc danh sách quá %d phút, dừng ở %d bài", limit_minutes, len(songs))
    if not songs:
        raise SunoError("no_songs", "Không đọc được bài nào trong danh sách của trang này")
    return [Song(sid, text) for sid, text in songs.items()]


# ---- one download ----

class Catcher:
    """Every file Chrome downloads, in any tab, and every tab that opens an audio file directly."""

    def __init__(self, context):
        self.context = context
        self.downloads = []
        for p in context.pages:
            self._watch(p)
        context.on("page", self._watch)

    def _watch(self, page):
        page.on("download", lambda d: self.downloads.append(d))

    def reset(self):
        self.downloads.clear()

    def audio_tab(self, fmt):
        for p in self.context.pages:
            m = AUDIO_URL_RE.search(urlparse(p.url).path)
            if m and m.group(1).lower() == fmt:
                return p
        return None


def _song_title(page):
    loc = page.locator(SEL["song_title"]).first
    title = _text(loc).split("\n")[0] if _visible(loc) else ""
    if not title:
        try:
            title = page.evaluate("() => { const m = document.querySelector('meta[property=\"og:title\"]'); "
                                  "return m ? m.content : document.title; }") or ""
        except Exception:
            title = ""
        title = re.sub(r"\s*\|\s*Suno.*$", "", title).strip()
    return title


def song_lyrics(page):
    """The lyrics the song page shows, or "" (none found: never an error)."""
    try:
        return page.evaluate(JS_LYRICS, SEL["lyrics"]) or ""
    except Exception:
        return ""


def _someone_elses(page):
    """Is this song page someone else's song? suno.com puts a Follow button by the artist's name, under the song's
    title, on other people's songs only. Only buttons near the title count (a list of other songs on the page may
    have its own)."""
    title = page.locator(SEL["song_title"]).first
    try:
        box = title.bounding_box() if _visible(title) else None
    except Exception:
        box = None
    for b in page.locator('button, [role="button"]').all():
        if not _visible(b):
            continue
        label = _text(b) or (b.get_attribute("aria-label") or "")
        if not SEL["text_follow"].search(label):
            continue
        if box is None:
            return True
        try:
            at = b.bounding_box()
        except Exception:
            at = None
        if at and box["y"] - 40 <= at["y"] <= box["y"] + box["height"] + 260 and \
                box["x"] - 80 <= at["x"] <= box["x"] + max(box["width"], 300) + 500:
            return True
    return False


def _dialog_format(page, fmt):
    """The format's row in Suno's download box (Download 'title': M4A, MP3, WAV...), or None."""
    want = SEL["text_dialog_format"][fmt]
    for box in page.locator(SEL["dialog"]).all():
        if not _visible(box):
            continue
        for row in box.locator(SEL["dialog_option"]).all():
            if _visible(row) and want.search(_text(row)):
                return row
    return None


def _chosen(row):
    """Is this row of the download box chosen? Its aria-checked / aria-pressed... when it has one, else its check
    mark (suno.com, October 2026: a chosen row shows one, the others none)."""
    for name in ("aria-checked", "aria-selected", "aria-pressed", "data-state", "data-selected", "data-checked"):
        try:
            value = row.get_attribute(name)
        except Exception:
            value = None
        if value is not None:
            return value.lower() in ("true", "checked", "on", "active", "selected", "")
    try:
        return any(_visible(mark) for mark in row.locator(SEL["dialog_check"]).all())
    except Exception:
        return False


def _box_rows(page):
    """The format rows of the open download box: [(row, its text)]."""
    rows = []
    for box in page.locator(SEL["dialog"]).all():
        if not _visible(box):
            continue
        for row in box.locator(SEL["dialog_option"]).all():
            text = _text(row) if _visible(row) else ""
            if SEL["text_dialog_row"].search(text):
                rows.append((row, text))
    return rows


def _pick_format(page, fmt):
    """The download box lets several rows be chosen at once (MP3 at first) and downloads every chosen one: the
    format's row is chosen, then every other chosen row unchosen, so the box gives that one file."""
    want = SEL["text_dialog_format"][fmt]
    for _ in range(8):
        rows = _box_rows(page)
        mine = [row for row, text in rows if want.search(text)]
        if not mine:
            break
        others = [row for row, text in rows if not want.search(text) and _chosen(row)]
        if _chosen(mine[0]) and not others:
            return
        row = mine[0] if not _chosen(mine[0]) else others[0]
        was = _chosen(row)
        row.click()
        _poll(page, lambda: _chosen(row) != was, 2000)
    raise SunoError("stuck", f"Không chọn được riêng dòng {fmt.upper()} trong hộp Download của Suno")


def _open_format_item(page, fmt):
    """More options → Download → WAV/MP3 (the format's row in the download box, or in the older menu); returns it,
    ready to click."""
    more = page.locator(SEL["more"]).first
    try:
        more.wait_for(state="visible", timeout=15_000)
    except Exception:
        raise SunoError("stuck", "Không thấy nút More options (⋯) ở trang bài hát")
    if _someone_elses(page):
        raise SunoError("not_mine", "Bài của người khác (cạnh tên bài có nút Follow): bỏ qua, không bấm tải")
    want = SEL["text_format"][fmt]

    def format_item():
        return _find_text(page, SEL["menu_item"], want)

    def format_anywhere():
        return format_item() or _dialog_format(page, fmt)

    def menu():
        item = format_anywhere()
        if item:
            return "item", item
        down = _find_text(page, SEL["menu_item"], SEL["text_download"])
        return ("download", down) if down else None

    for _ in range(3):  # a click before the page is ready does nothing: open the menu again
        more.click()
        kind, loc = _poll(page, menu, 3000) or (None, None)
        if kind == "item":
            return loc
        if kind == "download":
            if not _enabled(loc):
                raise SunoError("not_ready", "Suno chưa cho tải bài này (bài chưa tạo xong hoặc bị lỗi)")
            loc.hover()
            item = _poll(page, format_item, 1500)
            if not item:
                loc.click()  # (the download box opens on a click)
                item = _poll(page, format_anywhere, 5000)
            if item:
                return item
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    raise SunoError("stuck", f"Không thấy mục Download → {fmt.upper()} trong menu của bài hát")


def _answer_dialog(page, clicked):
    """Suno's download box: presses its Download button once it is ready. Never presses anything in a box that
    offers to buy or upgrade; such a box, or one saying the downloads are used up, stops the run."""
    for box in page.locator(SEL["dialog"]).all():
        if not _visible(box):
            continue
        text = _text(box)
        go = []
        for b in box.locator(SEL["dialog_button"]).all():
            label = _text(b) or (b.get_attribute("aria-label") or "")
            if SEL["text_go"].search(label):
                go.append((label, b))
        if SEL["text_none_left"].search(text):
            raise SunoError("limit", "Hộp Download của Suno ghi Downloads 0: hết lượt tải của gói (tới ngày làm mới "
                                     "ghi trong hộp). Tool dừng, không bấm gì")
        if SEL["text_buy"].search(text) or (SEL["text_limit"].search(text) and not go):
            raise SunoError("limit", f"Suno báo hết lượt tải của gói: \"{text[:160]}\". Tool dừng, không mua thêm")
        for label, b in go:
            if _enabled(b) and time.monotonic() - clicked.get(label, 0) > 10:
                b.click()
                clicked[label] = time.monotonic()
                return


def download_song(page, catcher, song, fmt, dest, log, timeout_seconds=300):
    """Downloads one song through its page's Download button into `dest`. Returns (the title the page shows, the
    lyrics it shows or "")."""
    page.goto(song.link, wait_until="domcontentloaded", timeout=90_000)
    catcher.reset()
    try:
        item = _open_format_item(page, fmt)
    except SunoError as e:
        if e.code == "not_mine" and not song.title:
            song.title = _song_title(page)  # (for danh-sach.csv)
        if e.code == "stuck" and page_state(page, wait_seconds=5)[0] != "in":
            raise SunoError("not_signed_in", "Tài khoản Suno đã bị đăng xuất. Chạy lại: suno login <tên>")
        raise
    title = song.title or _song_title(page)
    lyrics = song_lyrics(page)
    if not _enabled(item):
        raise SunoError("not_ready", f"Suno chưa cho tải bài này dạng {fmt.upper()} (bài chưa tạo xong hoặc bị lỗi)")
    if _dialog_format(page, fmt) is not None:  # the download box: a click on a row chooses or unchooses it
        _pick_format(page, fmt)
        page.wait_for_timeout(300)
    else:
        item.click()
    clicked = {}
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if catcher.downloads:  # the file in the format asked for, if several came
            d = next((x for x in reversed(catcher.downloads) if x.suggested_filename.lower().endswith("." + fmt)),
                     catcher.downloads[-1])
            failure = d.failure()
            if failure:
                raise SunoError("stuck", f"Chrome tải file lỗi: {failure}")
            d.save_as(str(dest))
            break
        tab = catcher.audio_tab(fmt)
        if tab:  # Suno opened the file itself instead of downloading it: take the same file
            r = page.context.request.get(tab.url, timeout=timeout_seconds * 1000)
            if not r.ok:
                raise SunoError("stuck", f"Không lấy được file {fmt.upper()} (HTTP {r.status})")
            dest.write_bytes(r.body())
            if tab is page:
                page.go_back()
            else:
                tab.close()
            break
        _answer_dialog(page, clicked)
        page.wait_for_timeout(250)
    else:
        raise SunoError("stuck", f"Đã bấm tải {fmt.upper()} nhưng sau {timeout_seconds} giây vẫn chưa nhận được file")
    page.keyboard.press("Escape")  # close the download box, if it stays open
    return title, lyrics


# ---- stems & MIDI ----

STEM_FILES = ("wav", "mp3", "midi")
STEMS_WAIT = 20 * 60  # seconds: extracting the stems, then making the files (MIDI takes longer)

# Whether a row of the stems' Download box is ticked: true, false, or null when the page does not say. The row's own
# box only: climbing from the label stops before an element that holds another row too. Without an aria-checked
# (suno.com marks its choices with a check mark, an svg, and nothing else), the row's check mark tells.
JS_TICKED = r"""(el) => {
  const names = /^(mp3|wav|midi)\b/i;
  const sel = '[role="checkbox"], [aria-checked], input[type="checkbox"], [data-state="checked"], [data-state="unchecked"]';
  const rows = (n) => [...n.querySelectorAll('*')].filter(e => e.children.length === 0
    && names.test((e.textContent || '').trim())).length;
  for (let r = el, i = 0; r && i < 5; r = r.parentElement, i++) {
    if (i > 0 && rows(r) > 1) break;
    const b = r.matches(sel) ? r : r.querySelector(sel);
    if (!b) continue;
    if (b.matches('input')) return b.checked;
    for (const a of ['aria-checked', 'data-state']) {
      const v = b.getAttribute(a);
      if (v != null) return ['true', 'checked', 'on'].includes(v.toLowerCase());
    }
  }
  for (let r = el, i = 0; r && i < 5; r = r.parentElement, i++) {
    if (i > 0 && rows(r) > 1) break;
    if (r.querySelector('svg')) return true;
    if (i > 0 && r.querySelector('[class*="check" i], [class*="tick" i]')) return false;
  }
  return null;
}"""


def _boxes(page, pattern=None):
    """The boxes (dialogs) shown now, the newest last; with `pattern`, only those whose text matches it."""
    found = []
    for box in page.locator(SEL["dialog"]).all():
        if _visible(box) and (pattern is None or pattern.search(_text(box))):
            found.append(box)
    return found


def _in_box(box, pattern, selector=None, text_only=False):
    """The last visible element of the box whose own text matches `pattern` (or its aria-label, unless text_only:
    an icon's "Download" is not the box's Download button)."""
    hit = None
    for el in box.locator(selector or 'button, [role="button"], [role="tab"]').all():
        if not _visible(el):
            continue
        text = _text(el)
        if not text and not text_only:
            try:
                text = el.get_attribute("aria-label") or ""
            except Exception:
                text = ""
        if pattern.search(text):
            hit = el
    return hit


def _stop_if_buy(page):
    """A box that offers to buy or upgrade, or says the credits are used up: the run stops, nothing is pressed."""
    for box in _boxes(page):
        text = _text(box)
        if SEL["text_buy"].search(text) or SEL["text_no_credits"].search(text):
            raise SunoError("limit", f"Suno báo hết credit hoặc mời mua thêm: \"{text[:160]}\". Tool dừng, không mua")


def download_stems(page, catcher, song, dest, log, files=STEM_FILES, tempo="follow", extract=True,
                   timeout_seconds=STEMS_WAIT):
    """A song's Stems & MIDI: the files Chrome receives, saved into the folder `dest`. Returns (title, [paths])."""
    page.goto(song.link, wait_until="domcontentloaded", timeout=90_000)
    catcher.reset()
    try:
        _open_format_item(page, "wav")  # (opens the download box: More options → Download)
    except SunoError as e:
        if e.code == "not_mine" and not song.title:
            song.title = _song_title(page)
        raise
    title = song.title or _song_title(page)
    box = (_boxes(page) or [None])[-1]
    manage = _in_box(box, SEL["text_manage"]) if box is not None else None
    if box is None or manage is None or not SEL["text_stems_row"].search(_text(box)):
        raise SunoError("stuck", "Không thấy mục Stems & MIDI → Manage trong hộp Download của Suno")
    manage.click()
    stems_box = _poll(page, lambda: (_boxes(page, SEL["text_stems_box"]) or [None])[-1], 15_000)
    if stems_box is None:
        raise SunoError("stuck", "Bấm Manage nhưng không thấy hộp Extract Stems and MIDI")
    tab = _in_box(stems_box, SEL["text_auto_split"])
    if tab is not None:
        tab.click()
        page.wait_for_timeout(500)

    def ready():
        box = (_boxes(page, SEL["text_stems_box"]) or [None])[-1]
        go = _in_box(box, SEL["text_plain_download"], text_only=True) if box is not None else None
        return go if go is not None and _enabled(go) else None

    deadline = time.monotonic() + timeout_seconds
    go = _poll(page, ready, 4000)
    if go is None:
        if not extract:
            raise SunoError("no_stems", "Bài chưa tách stems trên Suno (chưa bấm Extract): bỏ qua")
        _stop_if_buy(page)
        button = _in_box(stems_box, SEL["text_extract"])
        if button is None or not _enabled(button):
            raise SunoError("stuck", "Không thấy nút Extract trong hộp Extract Stems and MIDI")
        log.info("%s: đang tách stems trên Suno (Extract, Auto split): có thể mất vài phút", title)
        button.click()
        while go is None and time.monotonic() < deadline:
            _stop_if_buy(page)
            for confirm in _boxes(page):  # a box asking to confirm the extraction (it may say what it costs)
                text = _text(confirm)
                if (SEL["text_auto_split"].pattern and re.search(r"auto\s*split", text, re.I)
                        or SEL["text_files_box"].search(text) or SEL["text_stems_row"].search(text)):
                    continue  # (the stems box, its files box, the song's download box: never pressed from here)
                yes = _in_box(confirm, SEL["text_confirm"])
                if yes is not None and _enabled(yes):
                    yes.click()
            go = _poll(page, ready, 3000)
        if go is None:
            raise SunoError("stuck", f"Đã bấm Extract nhưng sau {timeout_seconds // 60} phút stems vẫn chưa xong")
    go.click()
    files_box = _poll(page, lambda: (_boxes(page, SEL["text_files_box"]) or [None])[-1], 15_000)
    if files_box is None:
        raise SunoError("stuck", "Bấm Download nhưng không thấy hộp chọn file (MP3, WAV, MIDI)")
    for kind, pattern in SEL["text_stem_file"].items():
        row = _in_box(files_box, pattern, SEL["stem_option"], text_only=True)
        if row is None:
            if kind in files:
                raise SunoError("stuck", f"Không thấy dòng {kind.upper()} trong hộp Download của stems")
            continue
        state = row.evaluate(JS_TICKED)
        if state is not None and state != (kind in files):
            row.click()
            page.wait_for_timeout(300)
            if row.evaluate(JS_TICKED) != (kind in files):
                raise SunoError("stuck", f"Không chọn được dòng {kind.upper()} trong hộp Download của stems")
        elif state is None and kind not in files:
            log.warning("%s: không biết dòng %s đang được chọn hay không: để nguyên", title, kind.upper())
    if "midi" in files:
        row = _in_box(files_box, SEL["text_tempo"][tempo], SEL["stem_option"], text_only=True)
        if row is not None:
            row.click()
            page.wait_for_timeout(300)
    _stop_if_buy(page)
    final = _in_box(files_box, SEL["text_plain_download"], text_only=True)
    if final is None or not _enabled(final):
        raise SunoError("stuck", "Không thấy nút Download trong hộp chọn file của stems")
    final.click()
    saved, last = [], None
    while time.monotonic() < deadline:
        while len(saved) < len(catcher.downloads):
            d = catcher.downloads[len(saved)]
            failure = d.failure()
            if failure:
                raise SunoError("stuck", f"Chrome tải file stems lỗi: {failure}")
            name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", d.suggested_filename or "stems.zip").strip(" .") or "stems.zip"
            path = dest / f"{len(saved) + 1:02d}-{name}"
            d.save_as(str(path))
            saved.append(path)
            last = time.monotonic()
        if saved and time.monotonic() - last > 10:  # no other file for a while: that was all
            break
        _stop_if_buy(page)
        page.wait_for_timeout(500)
    if not saved:
        raise SunoError("stuck", f"Đã bấm tải stems nhưng sau {timeout_seconds // 60} phút vẫn chưa nhận được file")
    for _ in range(3):  # close the boxes
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
    return title, saved


def save_failure(page, path_stem):
    """A screenshot of the window, and the open menus and boxes plus the page's button labels (no whole page: it holds
    account data), for fixing SEL."""
    try:
        page.screenshot(path=f"{path_stem}.png")
    except Exception:
        pass
    try:
        html = page.evaluate(r"""() => {
          const parts = [...document.querySelectorAll('[role="dialog"], [role="alertdialog"], [role="menu"]')]
            .map(e => e.outerHTML);
          const labels = [...document.querySelectorAll('button, [role="button"], [role="menuitem"]')]
            .map(b => (b.getAttribute('aria-label') || '') + ' | ' + (b.innerText || '').trim().split('\n')[0])
            .map(t => t.replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, '<email>').slice(0, 80));
          const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;');
          return '<p>' + esc(location.pathname) + '</p>' + parts.join('\n<hr>\n')
            + '<pre>' + esc(labels.join('\n')) + '</pre>';
        }""")
        with open(f"{path_stem}.html", "w", encoding="utf-8") as f:
            f.write(html)
    except Exception:
        pass
