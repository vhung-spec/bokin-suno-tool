"""A stand-in for the Suno command line (suno/bokin_suno.py) in the app's tests: it writes what the real one writes
to the file BOKIN_STUDIO_OUTPUT names, and stops a download once the BOKIN_SUNO_STOP file appears.

  stub_suno.py --data DIR [--headless] [--chrome PATH] <command> ...
"""
import os
import sys
import time

args = sys.argv[1:]
data = args[args.index("--data") + 1]
args = args[args.index("--data") + 2:]
while args and args[0] in ("--headless", "--chrome"):
    args = args[2:] if args[0] == "--chrome" else args[1:]
out = open(os.environ["BOKIN_STUDIO_OUTPUT"], "a", encoding="utf-8", buffering=1)
with open(os.path.join(data, "args.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(args))
cmd = args[0]
if cmd == "list":
    for n, title in enumerate(["Mưa đêm", "<b>Đậm</b>"], 1):
        out.write(f"{n}\t{title}\thttps://suno.com/song/{n:08d}-0000-0000-0000-000000000000\n")
    out.write("12:00:00  Có 2 bài ở link này\n")
elif cmd == "download":
    total = 5
    for n in range(1, total + 1):
        if os.path.exists(os.environ["BOKIN_SUNO_STOP"]):
            out.write("12:00:00  Đã dừng: Đã dừng theo yêu cầu\n")
            sys.exit(1)
        out.write(f"12:00:00  [{n}/{total}] Bài {n}: xong → Bài {n}.wav\n")
        time.sleep(float(os.environ.get("STUB_PACE", "0.05")))
    out.write("12:00:00  Tổng: 5 bài tải xong, 0 bài lỗi\n")
elif cmd == "login":
    out.write("12:00:00  Mở Chrome cho tài khoản\n")
    time.sleep(float(os.environ.get("STUB_LOGIN_WAIT", "0")))
    out.write("12:00:00  Đã lưu tài khoản\n")
else:
    out.write(f"12:00:00  {cmd}: xong\n")
sys.exit(0)
