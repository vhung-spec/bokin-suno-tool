"""Self-update from the GitHub releases of vhung-spec/bokin-suno-tool: the repository is public, so its releases
download without a login or a key. (Adapted from Bokin Suno Master's bokin_suno/updater.py, itself from Bokin FX.)

The repository also publishes Bokin Suno Master, whose installed apps read the manifest of the release GitHub marks
"Latest". Bokin Suno Studio's releases are therefore never "Latest" (the workflow publishes them with
--latest=false) and the app does not look there:

- each version is a release tagged studio-v<version> with the installer BokinSunoStudio-Setup-<version>.exe;
- one release tagged studio-latest (also never "Latest") always carries the manifest of the newest version,
  bokin-suno-studio-latest.json (its version, the installer's name, size and SHA-256), replaced by the workflow
  after it has built, installed and tested that version, and a copy of the installer under a fixed name
  (BokinSunoStudio-Setup.exe) for the download link in the guide.

AutoUpdate looks when the app starts, every 5 minutes, and when the page asks. It reads that manifest as a plain
download (github.com/.../releases/download/studio-latest/...), not through GitHub's API: without a login the API
answers 60 requests an hour for each Internet connection, and the computers of an office share one. Only if there
is no manifest is the API's list read (releases tagged studio-v only), and there the installer's SHA-256 is the
asset's "digest", else the "SHA-256:" line the workflow writes into the release notes. A release whose file cannot
be checked is never used. The installer is fetched in the background and kept only if its size and SHA-256 are the
published ones; a download that breaks off goes on from where it stopped next time.

Certificates: Python checks GitHub's against the roots Windows has. A Windows that has never fetched GitHub's root
refuses it ("unable to get local issuer certificate"); then the look is made again with Windows' own check
(truststore), and every look after it in this run too (system_context()).

The installer runs when the app quits by itself, or at once when the page asks ("Cập nhật ngay"), and then starts
the app again. Only api.github.com and GitHub's download servers are contacted, with nothing about the computer.
Whoever can publish releases in that repository can update every installed app: keep that account protected.
"""
import collections
import hashlib
import json
import os
import re
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.request

SITE = "https://github.com/vhung-spec/bokin-suno-tool"  # the releases as plain downloads
RELEASES = "https://api.github.com/repos/vhung-spec/bokin-suno-tool/releases?per_page=50"
MANIFEST = "bokin-suno-studio-latest.json"
CHANNEL = "studio-latest"  # the release that carries the newest manifest
TAG = "studio-v"
INSTALLER = re.compile(r"^BokinSunoStudio-Setup-[0-9.]+\.exe$")
CHECK_EVERY = 5 * 60
SOONEST = 60  # seconds between two checks the page asks for

Release = collections.namedtuple("Release", "version numbers url name size sha256")


def parse_version(text):
    """'1.0.12' -> (1, 0, 12); None for 'dev' and anything else that is not a version number."""
    parts = str(text).strip().split(".")
    if not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


_system = None  # Windows' own certificate check (system_context())
_system_first = False  # Python's own check refused GitHub's certificate: Windows' from then on, this run of the app


def system_context():
    """An SSL context that checks a certificate as Windows itself does (truststore: the roots Windows has and those
    it fetches when it lacks one, as Edge did); None where it is not to be had."""
    global _system
    if _system is None:
        try:
            import truststore
        except ImportError:  # (a build from the source folder without it, not Windows: Python's own check only)
            return None
        _system = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return _system


def _refused(error):
    """Did the certificate check refuse the server's certificate (not reaching it, or any other error)?"""
    return isinstance(error, urllib.error.URLError) and isinstance(error.reason, ssl.SSLCertVerificationError)


def _open(url, accept, start=0):
    """GitHub's answer (one thread only: the look's own, AutoUpdate.check()). A certificate Python's own check refuses
    is checked again as Windows checks it, and from then on so."""
    global _system_first
    headers = {"Accept": accept, "User-Agent": "BokinSunoStudio-update"}
    if start:
        headers["Range"] = f"bytes={start}-"
    request = urllib.request.Request(url, headers=headers)
    if not _system_first:
        try:
            return urllib.request.urlopen(request, timeout=60)
        except urllib.error.URLError as e:
            if not _refused(e) or system_context() is None:
                raise
            print(f"update check: {e.reason}; checked again as Windows checks it", flush=True)
            _system_first = True
    return urllib.request.urlopen(request, timeout=60, context=system_context())


def _sources():
    """(the site whose newest release's manifest is read first or None, the API). A test's stand-in for GitHub
    (BOKIN_UPDATE_API, and BOKIN_UPDATE_SITE for its manifest) never leads to the real one."""
    api = os.environ.get("BOKIN_UPDATE_API")
    return (os.environ.get("BOKIN_UPDATE_SITE"), api) if api else (SITE, RELEASES)


def latest():
    """The newest published release that has a checkable installer, or None: from the manifest of the studio-latest
    release, else (none there, or not one to use) from the API's list."""
    site, api = _sources()
    if site:
        try:
            return from_manifest(site)
        except (urllib.error.HTTPError, ValueError):  # (no manifest: a release before it had one; or none to use)
            pass  # (GitHub out of reach: that is the answer, no second wait)
    return from_api(api)


def from_manifest(site):
    """The release a manifest describes (a plain download from the studio-latest release, no API). ValueError if it
    is not one to use."""
    with _open(f"{site}/releases/download/{CHANNEL}/{MANIFEST}", "application/octet-stream") as r:
        m = json.loads(r.read(1 << 16))
    numbers, name = parse_version(m.get("version", "")), m.get("name")
    sha, size = str(m.get("sha256", "")).lower(), m.get("size")
    if not numbers or not isinstance(name, str) or not INSTALLER.match(name) or not re.fullmatch(r"[0-9a-f]{64}", sha) \
            or not isinstance(size, int) or size <= 0:
        raise ValueError("the manifest is not one to use")
    version = ".".join(map(str, numbers))
    return Release(version, numbers, f"{site}/releases/download/{TAG}{version}/{name}", name, size, sha)


def from_api(api):
    """The newest release with a checkable installer in the API's list, or None."""
    with _open(api, "application/vnd.github+json") as r:
        listing = json.loads(r.read())
    found = None
    for rel in listing:
        tag = rel.get("tag_name") or ""
        numbers = parse_version(tag[len(TAG):]) if tag.startswith(TAG) else None
        if not numbers or rel.get("draft") or rel.get("prerelease") or (found and numbers <= found.numbers):
            continue
        for asset in rel.get("assets") or []:
            if not INSTALLER.match(asset.get("name") or ""):
                continue
            sha = (asset.get("digest") or "").lower().partition("sha256:")[2]
            if not re.fullmatch(r"[0-9a-f]{64}", sha):
                noted = re.search(r"SHA-256:\s*([0-9a-fA-F]{64})", rel.get("body") or "")
                sha = noted.group(1).lower() if noted else ""
            if sha:
                found = Release(".".join(map(str, numbers)), numbers, asset["browser_download_url"],
                                asset["name"], asset.get("size"), sha)
            break
    return found


def verified(path, release):
    if release.size is not None and os.path.getsize(path) != release.size:
        return False
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(1 << 20)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest() == release.sha256


def _keep_only(folder, name):
    for other in os.listdir(folder):
        if other != name:
            try:
                os.remove(os.path.join(folder, other))
            except OSError:
                pass


def fetch(release, folder):
    """The release's installer in `folder`, downloaded once and verified. A download that broke off goes on from
    where it stopped (when the server can send the rest only). Older files there are deleted only once this one is
    in place, so a ready installer never disappears before its replacement is."""
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, release.name)
    if os.path.exists(target) and verified(target, release):
        _keep_only(folder, release.name)
        return target
    partial = target + ".download"
    have = os.path.getsize(partial) if os.path.exists(partial) else 0
    if release.size is None or have >= release.size:
        have = 0  # (nothing to go on from: from the start)
    with _open(release.url, "application/octet-stream", have) as r:
        if r.status != 206 or not (r.headers.get("Content-Range") or "").startswith(f"bytes {have}-"):
            have = 0  # (the server sent the whole file)
        with open(partial, "ab" if have else "wb") as f:
            while True:
                block = r.read(1 << 20)
                if not block:
                    break
                f.write(block)
    if not verified(partial, release):
        os.remove(partial)
        raise ValueError("downloaded installer does not match the published SHA-256")
    os.replace(partial, target)
    _keep_only(folder, release.name)
    return target


def reason(error):
    """Why a look failed, for the page: "limit" (GitHub's API refused: its limit of requests for this Internet
    connection), "github" (GitHub answered with another error), "cert" (its certificate refused, Windows' own check
    too: the computer's clock wrong, an antivirus or a company network replacing it with one this computer does not
    trust), "offline" (GitHub could not be reached: no connection, its name not found, a firewall), "other"."""
    if isinstance(error, urllib.error.HTTPError):
        if error.code == 429 or (error.code == 403 and (error.headers or {}).get("X-RateLimit-Remaining") == "0"):
            return "limit"
        return "github"
    if _refused(error):
        return "cert"
    if isinstance(error, OSError):  # (URLError, a time-out)
        return "offline"
    return "other"


class AutoUpdate:
    """state: what the page shows. ready = an installer for a newer version is downloaded and verified."""

    def __init__(self, current, folder, every=CHECK_EVERY):
        self.numbers, self.folder, self.every = parse_version(current), folder, every
        self.installer = None
        self.state = {"current": current, "available": None, "ready": False, "error": None, "reason": None,
                      "checked": None, "downloading": None}
        self.wake = threading.Event()

    def start(self):
        if self.numbers is not None:  # a build from the source folder ("dev") never updates itself
            threading.Thread(target=self._run, daemon=True, name="studio-update").start()
        return self

    def _run(self):
        time.sleep(3)
        while True:
            self.check()
            self.wake.wait(self.every)
            self.wake.clear()

    def check_soon(self):
        """Look again now (the page asked), unless that was done a moment ago. True if a look was started."""
        if self.state.get("downloading") or time.time() - (self.state.get("checked") or 0) <= SOONEST:
            return False
        self.wake.set()
        return True

    def check(self):
        """One look; "checked" is set once it is over (the installer downloaded too), so the page can tell."""
        try:
            release = latest()
            if release and release.numbers > self.numbers:
                self.state["downloading"] = release.version
                installer = fetch(release, self.folder)
                self.installer = installer
                self.state.update(available=release.version, ready=True)
                print(f"update {release.version} ready: it is installed when the app closes", flush=True)
            self.state.update(error=None, reason=None)
        except Exception as e:  # noqa: BLE001 - offline or GitHub busy: next time
            self.state.update(error=f"{type(e).__name__}: {e}"[:200],
                              reason="download" if self.state["downloading"] else reason(e))
            print(f"update check: {self.state['error']}", flush=True)
        finally:
            self.state.update(downloading=None, checked=time.time())

    def run_installer(self, restart):
        """Start the verified installer on its own, silently (it closes this app). False if there is none."""
        if not self.installer or not os.path.exists(self.installer):
            return False
        args = [self.installer, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
        if restart:
            args.append("/RELAUNCH=1")
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        subprocess.Popen(args, close_fds=True, creationflags=flags)
        print(f"running the installer of {self.state['available']}", flush=True)
        return True
