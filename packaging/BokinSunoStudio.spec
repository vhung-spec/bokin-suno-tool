# PyInstaller recipe for Bokin Suno Studio: one folder, packed into a single installer by BokinSunoStudio.iss.
# Built by .github/workflows/bokin-suno-studio.yml:
#   python packaging/make_studio_icon.py
#   pyinstaller packaging/BokinSunoStudio.spec --noconfirm      -> dist/BokinSunoStudio/
#
# Besides the Python packages (bokin_studio, and bokin_suno for mastering) the bundle carries, at the same places as
# in the repository: Lời Đồng Âm (loi-dong-am/), Bokin Suno Master's page, and the Suno downloader (suno/*.py: run
# as `BokinSunoStudio.exe suno ...`, imported from that folder, so they are data here) with patchright and its
# driver (node and its package). The browser is the Google Chrome installed on the computer (channel "chrome"), not
# a copy in the bundle: Chrome keeps itself up to date.
import os

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821 (SPECPATH is set by PyInstaller)


def files(folder, names):
    return [(os.path.join(ROOT, folder, name), folder) for name in names]


datas = (files("bokin_studio/static", ["index.html", "logo.svg"]) + files("bokin_suno/static", ["index.html"])
         + files("loi-dong-am", ["index.html", "engine.js", "hyphen-en-us.js"])
         + files("suno", ["bokin_suno.py", "web.py", "folder.py"]))
for package in ("bokin_studio", "bokin_suno"):
    if os.path.exists(os.path.join(ROOT, package, "version.txt")):
        datas += files(package, ["version.txt"])

a = Analysis(
    [os.path.join(SPECPATH, "bokin_suno_studio.py")],  # noqa: F821
    pathex=[ROOT],
    # libsndfile (WAV, FLAC, MP3) and its licence come with soundfile, in _soundfile_data; truststore's licence (MIT)
    # with it (Windows' own certificate check: bokin_studio/updater.py); patchright's driver and licence
    binaries=collect_dynamic_libs("_soundfile_data"),
    datas=datas + collect_data_files("_soundfile_data") + copy_metadata("truststore")
    + collect_data_files("patchright") + copy_metadata("patchright"),
    hiddenimports=collect_submodules("uvicorn") + collect_submodules("patchright")
    + ["_soundfile_data", "multipart", "python_multipart", "truststore", "bokin_studio.selftest",
       "bokin_suno.selftest", "greenlet", "pyee",
       # what suno/*.py use (they are data in the bundle, so PyInstaller does not see their imports)
       "argparse", "csv", "logging.handlers", "unicodedata", "dataclasses", "tempfile", "shutil", "importlib.util"],
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "PIL"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="BokinSunoStudio",
          icon=os.path.join(SPECPATH, "studio.ico"), console=False, upx=False)  # noqa: F821
coll = COLLECT(exe, a.binaries, a.datas, name="BokinSunoStudio", upx=False)
