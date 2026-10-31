"""The "Chọn…" button's folder dialog, for real on Windows: it opens, on top of every other window (not behind the
app's), and a folder with Vietnamese letters comes back as it is; Cancel gives nothing."""
import os
import threading
import time
import warnings

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows' own folder dialog")


def dialogs():
    """The dialog windows (#32770) shown now: {hwnd: (title, program)}."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    found = {}

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        name = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, name, 64)
        if name.value == "#32770" and user32.IsWindowVisible(hwnd):
            title = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title, 256)
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            exe, size = ctypes.create_unicode_buffer(520), wintypes.DWORD(520)
            proc = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
            if proc:
                kernel32.QueryFullProcessImageNameW(proc, 0, exe, ctypes.byref(size))
                kernel32.CloseHandle(proc)
            found[hwnd] = (title.value, exe.value)
        return True

    user32.EnumWindows(each, 0)
    return user32, found


def find_dialog(before, seconds=60):
    """The picker's dialog: one that was not shown before it was opened (another program's may be up)."""
    if before:
        warnings.warn(f"other dialogs already shown: {list(before.values())}")  # (in the test summary)
    deadline = time.time() + seconds
    while time.time() < deadline:
        user32, now = dialogs()
        new = [h for h in now if h not in before]
        if new:
            return user32, new[0]
        time.sleep(0.3)
    raise AssertionError("the folder dialog did not open")


def on_top(user32, hwnd):
    """The dialog, or the window that owns it, stays above windows that are not "always on top"."""
    GW_OWNER, GWL_EXSTYLE, WS_EX_TOPMOST = 4, -20, 0x8
    owner = user32.GetWindow(hwnd, GW_OWNER)
    return any(w and user32.GetWindowLongW(w, GWL_EXSTYLE) & WS_EX_TOPMOST for w in (hwnd, owner))


def run_picker(start):
    from bokin_studio.app import pick_folder

    result = {}
    t = threading.Thread(target=lambda: result.update(value=pick_folder(start)), daemon=True)
    t.start()
    return t, result


def test_ok_gives_the_folder(tmp_path):
    folder = tmp_path / "Nhạc Suno thử"
    folder.mkdir()
    before = dialogs()[1]
    t, result = run_picker(str(folder / "chưa có"))  # a folder not made yet: starts from its parent
    user32, dlg = find_dialog(before)
    assert on_top(user32, dlg), "the dialog must open on top of the app's window"
    time.sleep(1)
    user32.PostMessageW(dlg, 0x0111, 1, 0)  # WM_COMMAND IDOK: the OK button
    t.join(60)
    assert result.get("value") == str(folder)


def test_cancel_gives_nothing(tmp_path):
    before = dialogs()[1]
    t, result = run_picker(str(tmp_path))
    user32, dlg = find_dialog(before)
    user32.PostMessageW(dlg, 0x0111, 2, 0)  # IDCANCEL
    t.join(60)
    assert result.get("value") == ""
