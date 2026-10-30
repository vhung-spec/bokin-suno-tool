"""End-to-end test of Bokin Suno against the stand-in Suno (tests/fake_suno.py), with a real Chrome.

Runs the program as a person would (python suno/bokin_suno.py ...): sign in, check, a workspace whose list loads as
it scrolls, a few songs first (--limit), then the rest with a song still being made and a song page that fails once,
a second run that reads only the top of the list yet tries the unfinished song again, the lyrics kept next to each
song (none for an instrumental), the download box where several rows can be chosen (WAV alone is), MP3 through a
"uses 1 download" box opening in a new tab, several links at once (one of them bad), a Load more button, pages behind a
Next page button that stays enabled on the last page, the Stop button of Bokin Suno Studio, a Suno page
without window.Clerk (only Clerk's cookies tell who is signed in), share links (suno.com/s/...: the one song, never
the Similar list beside it), someone else's song (never downloaded), the plan's downloads used up (nothing
bought), a changed Suno page, the wrong account, a sign-out, removing the account.

  python tests/test_suno.py [--headless] [--chrome PATH] [--keep]
On Linux without a screen: xvfb-run -a python tests/test_suno.py
BOKIN_SUNO_CMD (a JSON list) runs another program instead, e.g. the installed Bokin Suno Studio:
  ["C:/.../BokinSunoStudio.exe", "suno"]
whose output is read from the file BOKIN_STUDIO_OUTPUT names, as the app reads it (an installed app has no console).
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fake_suno import USER_ID, WORKSPACE, FakeSuno, audio_bytes, default_lyrics  # noqa: E402

PROG = HERE.parent / "suno" / "bokin_suno.py"
failures = []


def check(cond, what):
    print(("  ok   " if cond else "  FAIL ") + what, flush=True)
    if not cond:
        failures.append(what)


def read_list(folder):
    with open(folder / "danh-sach.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--chrome")
    ap.add_argument("--keep", action="store_true", help="keep the temporary folder")
    opts = ap.parse_args()

    fake = FakeSuno()
    titles = ["Mưa đêm", "Mưa đêm", "../../thoát ra", "CON", '=cmd|" /C calc"!A0', "<b>Đậm</b> & \"nháy\"",
              unicodedata.normalize("NFD", "Phố cũ")] + [f"Lofi số {n}" for n in range(1, 15)]
    ids = [fake.add_song(t, lyrics="" if t == "CON" else None) for t in titles[:10]]  # CON: an instrumental
    making = fake.add_song("Đang tạo", status="streaming")  # in the middle of the list
    ids += [fake.add_song(t) for t in titles[10:]]
    fake.start()
    # Linux: Chrome refuses a --user-data-dir with a long path, so the temporary folder stays short
    tmp = Path(tempfile.mkdtemp(prefix="sn-", dir=None if sys.platform == "win32" else "/tmp"))
    data = tmp / "data"
    env = dict(os.environ, BOKIN_SUNO_URL=fake.url, BOKIN_SUNO_DATA=str(data), BOKIN_SUNO_LOGIN_SETTLE="2",
               BOKIN_SUNO_KNOWN_STREAK="5", PYTHONIOENCODING="utf-8")
    base = json.loads(os.environ["BOKIN_SUNO_CMD"]) if os.environ.get("BOKIN_SUNO_CMD") else [sys.executable,
                                                                                                str(PROG)]
    if opts.headless:
        base.append("--headless")
    if opts.chrome:
        base += ["--chrome", opts.chrome]
    link = f"{fake.url}/create?wid={WORKSPACE}"

    def cli(*args, expect=0, contains=None):
        print(f"\n$ suno {' '.join(args)}", flush=True)
        output = tmp / "output.txt"
        if os.environ.get("BOKIN_SUNO_CMD"):
            output.write_text("", encoding="utf-8")
            env["BOKIN_STUDIO_OUTPUT"] = str(output)
        r = subprocess.run(base + list(args), env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900)
        out = r.stdout + r.stderr
        if os.environ.get("BOKIN_SUNO_CMD"):
            out += output.read_text(encoding="utf-8", errors="replace")
        print(out.rstrip())
        check(r.returncode == expect, f"exit code {r.returncode} == {expect}")
        if contains:
            check(contains.lower() in out.lower(), f"output mentions '{contains}'")
        return out

    def files(folder, fmt):
        return sorted(p for p in folder.glob(f"*.{fmt}"))

    try:
        nhac = tmp / "nhac"
        print("== self-test")
        cli("selftest", contains="selftest OK")

        print("== before signing in")
        cli("download", "suno1", link, "--out", str(nhac), expect=2, contains="chưa đăng nhập")
        cli("login", "tài khoản", expect=2, contains="không hợp lệ")

        print("== sign in")
        cli("login", "suno1", contains="Đã lưu tài khoản suno1")
        accounts = json.loads((data / "accounts.json").read_text(encoding="utf-8"))
        check(accounts.get("suno1", {}).get("user_id") == USER_ID, "accounts.json has the Suno user ID")
        check(fake.signins == 1, "signed in once")

        print("== a Suno page without window.Clerk (as suno.com on the owner's computer): Clerk's cookies tell")
        fake.config["clerk_global"] = False
        cli("login", "suno2", contains="Đã lưu tài khoản suno2")
        accounts = json.loads((data / "accounts.json").read_text(encoding="utf-8"))
        check(accounts.get("suno2", {}).get("user_id") == USER_ID, "the user ID read from the session cookie")
        cli("check", "suno2", contains="đang đăng nhập")
        cli("list", "suno2", link, contains=f"Có {len(fake.workspace)} bài")
        fake.config["clerk_global"] = True
        cli("remove", "suno2", contains="Đã xoá")
        fake.config["auto_signin"] = False
        cli("check", contains="đang đăng nhập")
        cli("accounts", contains="suno1")

        print("== links that are not a Suno workspace")
        cli("download", "suno1", "https://evil.example/create?wid=1", "--out", str(nhac), expect=2,
            contains="không phải link của Suno")
        cli("download", "suno1", f"{fake.url}/create?wid=nothing", "--out", str(nhac), expect=2,
            contains="Không thấy bài nào")

        print("== a few songs first")
        cli("download", "suno1", link, "--out", str(nhac), "--limit", "2", contains="2 bài tải xong")
        check(len(files(nhac, "wav")) == 2, "two WAV files")

        print("== the rest of the workspace; one song is still being made, one song page fails once")
        fake.fail_once = {ids[15]}
        out = cli("download", "suno1", link, "--out", str(nhac), expect=1, contains="19 bài tải xong, 1 bài lỗi")
        check("thử lại một lần" in out.lower() and not fake.fail_once, "the failing page was tried again")
        check("còn 1 bài, khoảng" in out, "time left shown")
        got = {p.name: p.read_bytes() for p in files(nhac, "wav")}
        check(len(got) == len(titles), f"{len(titles)} WAV files ({len(got)})")
        rows = read_list(nhac)
        by_id = {r["id"]: r for r in rows if r["trang_thai"] == "xong"}
        check(set(by_id) == set(ids), "danh-sach.csv lists every downloaded song once")
        failed_rows = [r for r in rows if r["trang_thai"] == "loi"]
        check([r["id"] for r in failed_rows] == [making] and "chưa cho tải" in failed_rows[0]["ghi_chu"],
              "the unfinished song listed as failed, with the reason")
        for sid in ids:
            rec = by_id.get(sid, {})
            check(got.get(rec.get("file")) == audio_bytes(sid, "wav"), f"{rec.get('file')} is that song's WAV")
        names = set(got)
        for name in ("Mưa đêm.wav", "Mưa đêm (2).wav", "thoát ra.wav", "_CON.wav", "Phố cũ.wav", "cmd C calc !A0.wav"):
            check(name in names, f"file name {name}")
        check(all(p.parent == nhac for p in nhac.rglob("*.wav")), "no file outside the folder")
        check(fake.stray not in {r["id"] for r in rows}, "the player's song skipped")
        raw = (nhac / "danh-sach.csv").read_text(encoding="utf-8-sig")
        check("'=cmd" in raw, "a title starting with = is not a formula in Excel")
        check(sorted(fake.counted) == sorted(ids), "Suno counted each downloaded song once")
        check(not list(nhac.glob("*.part")) and not list(nhac.glob(".*.part")), "no half-downloaded files left")
        for sid in ids:
            rec = by_id.get(sid, {})
            lyrics = nhac / Path(rec.get("file", "x")).with_suffix(".txt").name
            if fake.songs[sid]["lyrics"]:
                check(lyrics.is_file() and lyrics.read_text(encoding="utf-8").strip() == fake.songs[sid]["lyrics"],
                      f"{lyrics.name}: the song's lyrics")
            else:
                check(not lyrics.exists(), f"no lyrics file for the instrumental {rec.get('file')}")
        check(default_lyrics("x").count("\n\n") == 1, "lyrics keep their blank line")
        check(fake.picked and all(f == "wav" for _, f in fake.picked),
              "WAV alone chosen in the download box (MP3, chosen at first, unchosen)")

        print("== again, with the song finished and two new songs: only those three, reading only the top of the list")
        fake.songs[making]["status"] = "complete"
        new = [fake.add_song("Bài mới 1"), fake.add_song("Bài mới 2")]
        picked = len(fake.picked)
        out = cli("download", "suno1", link, "--out", str(nhac), contains="3 bài tải xong, 0 bài lỗi")
        check("dừng đọc danh sách" in out and "1 bài lần trước bị lỗi" in out, "top of the list, then the failed song")
        check(sorted(s for s, _ in fake.picked[picked:]) == sorted(new + [making]), "only the three were downloaded")
        check(all(r["trang_thai"] == "xong" for r in read_list(nhac)), "no failed song left in the list")
        picked = len(fake.picked)
        cli("download", "suno1", link, "--out", str(nhac), contains="0 bài cần tải")
        out = cli("download", "suno1", link, "--out", str(nhac), "--full", contains="0 bài cần tải")
        check("dừng đọc danh sách" not in out and f"Đọc được {len(fake.workspace)} bài" in out, "--full reads it all")
        check(len(fake.picked) == picked, "nothing downloaded twice")

        print("== the older menu (Download → MP3 Audio), a 'uses 1 download' box, the file opening in a new tab")
        fake.config.update(confirm=True, delivery="newtab", download_ui="menu")
        mp3 = tmp / "mp3"
        counted = len(fake.counted)
        cli("download", "suno1", link, "--out", str(mp3), "--format", "mp3", "--limit", "3", contains="3 bài tải xong")
        got = files(mp3, "mp3")
        check(len(got) == 3, "three MP3 files")
        check(all(p.read_bytes()[:3] == b"ID3" for p in got), "they are MP3")
        check(len(fake.counted) == counted, "songs already downloaded as WAV count no more")
        fake.config.update(confirm=False, delivery="attach", download_ui="box")

        print("== the download box whose rows say which is chosen (aria-pressed): WAV chosen before Unlock & Download")
        fake.config["box_aria"] = True
        aria = [fake.add_song("Hàng có aria 1"), fake.add_song("Hàng có aria 2")]
        cli("download", "suno1", link, "--out", str(nhac), contains="2 bài tải xong")
        check(all((s, "wav") in fake.picked for s in aria), "WAV downloaded through the box")
        fake.config["box_aria"] = False

        print("== several links at once, one of them bad")
        one = tmp / "vai-bai"
        cli("download", "suno1", f"{fake.url}/create?wid=nothing", f"{fake.url}/song/{ids[6]}?sh=abc",
            f"{fake.url}/song/{ids[5]}", f"{fake.url}/song/{ids[6]}", "--out", str(one), expect=1,
            contains="2 bài tải xong, 0 bài lỗi")
        check(sorted(p.name for p in files(one, "wav")) == ["Phố cũ.wav", "b Đậm b & nháy.wav"],
              "named after the song pages' titles, each song once")
        fake.config["delivery"] = "blob"

        print("== a Load more button instead of scrolling")
        fake.config["paging"] = "button"
        out = cli("list", "suno1", link, contains=f"Có {len(fake.workspace)} bài")
        check(fake.stray not in out, "the player's song is not listed")
        print("== pages, as on suno.com's Create page: Next page stays enabled on the last page and does nothing")
        fake.config["paging"] = "pages"
        started = time.monotonic()
        out = cli("list", "suno1", link, contains=f"Có {len(fake.workspace)} bài")
        check(len(fake.workspace) > 15 and all(s in out for s in fake.workspace), "every page read")
        check(time.monotonic() - started < 120, "stopped at the last page (not round and round)")
        fake.config["paging"] = "scroll"

        print("== the Stop button of Bokin Suno Studio")
        flag = tmp / "dung"
        flag.write_text("", encoding="utf-8")
        stop_later = fake.add_song("Chưa tải vì đã dừng")
        env["BOKIN_SUNO_STOP"] = str(flag)
        cli("download", "suno1", link, "--out", str(nhac), expect=1, contains="dừng theo yêu cầu")
        del env["BOKIN_SUNO_STOP"]
        check(stop_later not in {r["id"] for r in read_list(nhac)}, "nothing downloaded once stopped")
        fake.workspace.remove(stop_later)

        print("== a share link (suno.com/s/...) to one of the account's songs: that song only, not the Similar list")
        code = fake.add_share(ids[3])
        out = cli("list", "suno1", f"{fake.url}/s/{code}", contains="Có 1 bài")
        check(ids[3] in out and not any(s in out for s in fake.similar), "the shared song, none of the Similar list")
        picked = len(fake.picked)
        out = cli("download", "suno1", f"{fake.url}/s/{code}", "--out", str(tmp / "chia-se"), contains="1 bài tải xong")
        check([s for s, _ in fake.picked[picked:]] == [ids[3]], "only the shared song downloaded")

        print("== someone else's song (a Follow button by its artist): never downloaded")
        theirs = fake.add_song("Bài người khác", owner="other")
        picked, counted = len(fake.picked), len(fake.counted)
        cli("download", "suno1", link, "--out", str(nhac), contains="1 bài của người khác (bỏ qua)")
        check(len(fake.picked) == picked and len(fake.counted) == counted, "nothing pressed, no download used")
        row = [r for r in read_list(nhac) if r["id"] == theirs]
        check(row and row[0]["trang_thai"] == "nguoi_khac", "listed as someone else's song")
        cli("download", "suno1", link, "--out", str(nhac), contains="0 bài cần tải")
        check(len(fake.picked) == picked, "not tried again")
        code = fake.add_share(fake.similar[0])
        cli("download", "suno1", f"{fake.url}/s/{code}", "--out", str(tmp / "chia-se"),
            contains="1 bài của người khác (bỏ qua)")
        check(fake.similar[0] not in fake.counted, "a share link to someone else's song: nothing downloaded")
        fake.workspace.remove(theirs)

        print("== Stems & MIDI of a song whose stems are made already: no Extract, one zip unpacked in its folder")
        check(fake.stems_opened == [], "Stems & MIDI → Manage never opened by a plain download")
        fake.stems[ids[2]] = "ready"
        picked = len(fake.picked)
        cli("stems", "suno1", f"{fake.url}/song/{ids[2]}", "--out", str(nhac), contains="stems của 1 bài tải xong")
        row = {(r["id"], r["dinh_dang"]): r for r in read_list(nhac)}.get((ids[2], "stems"), {})
        stems = nhac / row.get("file", "?")
        check(row.get("trang_thai") == "xong" and stems.name.endswith(" - stems"), f"listed: {row.get('file')}")
        check(all((stems / k / f"Drums.{e}").is_file() for k, e in (("WAV", "wav"), ("MP3", "mp3"), ("MIDI", "mid"))),
              "WAV, MP3 and MIDI stems in their folders")
        check(not (nhac / "evil.txt").exists() and not (tmp / "evil.txt").exists(), "nothing written outside the folder")
        check(fake.extract_clicks == [] and len(fake.picked) == picked, "no Extract, no song download pressed")
        check(fake.stems_downloads[-1][1:] == ("wav,mp3,midi", "follow"), f"files and tempo {fake.stems_downloads}")
        cli("stems", "suno1", f"{fake.url}/song/{ids[2]}", "--out", str(nhac), contains="0 bài cần tải")
        check(len(fake.stems_downloads) == 1, "stems done before are not downloaded again")

        print("== download --stems: a new song downloaded, its stems extracted (Extract, after a box asking first)")
        fake.config["extract_confirm"] = True
        fresh = fake.add_song("Bài tách stems")
        cli("download", "suno1", link, "--out", str(nhac), "--stems", "--limit", "1", contains="1 bài tải xong")
        check(fake.extract_clicks == [fresh] and fake.stems_downloads[-1][0] == fresh, "Extract pressed for it, once")
        check(any((nhac / r["file"]).is_dir() for r in read_list(nhac) if r["id"] == fresh and r["dinh_dang"] ==
                  "stems"), "its stems folder")
        fake.config["extract_confirm"] = False

        print("== stems: only the files asked for, the MIDI's tempo fixed")
        fake.stems[ids[3]] = "ready"
        cli("stems", "suno1", f"{fake.url}/song/{ids[3]}", "--out", str(nhac), "--files", "wav,midi", "--tempo",
            "fixed", contains="stems của 1 bài tải xong")
        check(fake.stems_downloads[-1] == (ids[3], "wav,midi", "fixed"), f"WAV and MIDI, fixed {fake.stems_downloads}")

        print("== stems with the credits used up: stopped, Upgrade never pressed")
        fake.config["credits"] = 0
        broke = fake.add_song("Hết credit")
        cli("download", "suno1", link, "--out", str(nhac), "--stems", expect=1, contains="hết credit")
        check(broke not in fake.extract_clicks and "upgrade" not in fake.pressed, "nothing bought")
        fake.config["credits"] = None
        check(fake.pressed == [], f"never pressed: a single stem's own Download, Upgrade ({fake.pressed})")

        print("== the plan's downloads used up")
        fake.config["downloads_left"] = 1
        later = [fake.add_song("Hết lượt 1"), fake.add_song("Hết lượt 2")]
        cli("download", "suno1", link, "--out", str(nhac), expect=1, contains="Downloads 0")
        rows = {r["id"] for r in read_list(nhac)}
        check(later[1] in rows and later[0] not in rows, "the one allowed download made, then stopped")
        check(later[0] not in [s for s, _ in fake.picked], "the box said Downloads 0: nothing pressed")
        check(fake.buy_clicks == 0, "nothing bought")
        print("== the plan's downloads used up, the older menu: Suno's box with a Buy button")
        fake.config["download_ui"] = "menu"
        cli("download", "suno1", link, "--out", str(nhac), expect=1, contains="hết lượt tải")
        check(later[0] not in {r["id"] for r in read_list(nhac)} and fake.buy_clicks == 0, "stopped, nothing bought")
        fake.config["download_ui"] = "box"
        fake.config["downloads_left"] = None

        check(fake.pressed == [], f"Move to Trash, Download cover image, Manage never pressed ({fake.pressed})")

        print("== Suno's page changed")
        fake.config["more_label"] = "Song actions"
        for n in range(3):
            fake.add_song(f"Giao diện mới {n}")
        cli("download", "suno1", link, "--out", str(nhac), expect=1, contains="đổi giao diện")
        check(any(p.suffix == ".png" for p in (data / "logs").iterdir()), "a screenshot of the failure")
        check(any(p.suffix == ".html" for p in (data / "logs").iterdir()), "the page's buttons for fixing the tool")
        fake.config["more_label"] = "More options"

        print("== the wrong account")
        saved = (data / "accounts.json").read_text(encoding="utf-8")
        other = json.loads(saved)
        other["suno1"]["user_id"] = "user_someoneElse"
        (data / "accounts.json").write_text(json.dumps(other), encoding="utf-8")
        cli("download", "suno1", link, "--out", str(nhac), expect=2, contains="tài khoản Suno khác")
        (data / "accounts.json").write_text(saved, encoding="utf-8")

        print("== signed out")
        fake.sign_everyone_out()
        cli("check", "suno1", expect=1, contains="đăng xuất")
        cli("download", "suno1", link, "--out", str(nhac), expect=2, contains="đăng xuất")

        print("== remove the account")
        cli("remove", "suno1", contains="Đã xoá")
        check(not (data / "profiles" / "suno1").exists(), "profile deleted")
        check(json.loads((data / "accounts.json").read_text(encoding="utf-8")) == {}, "account forgotten")
    finally:
        fake.stop()
        if opts.keep or failures:
            print(f"\nkept {tmp}")
            logs = data / "logs" / "suno.log"
            if failures and logs.exists():
                print(logs.read_text(encoding="utf-8")[-6000:])
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'ALL OK' if not failures else f'{len(failures)} FAILED: ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
