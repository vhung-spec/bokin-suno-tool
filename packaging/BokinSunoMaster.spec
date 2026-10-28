# PyInstaller recipe for Bokin Suno Master: one folder, packed into a single installer by BokinSunoMaster.iss.
# Built by .github/workflows/bokin-suno-master.yml:
#   python packaging/make_icon.py
#   pyinstaller packaging/BokinSunoMaster.spec --noconfirm      -> dist/BokinSunoMaster/
import os

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821 (SPECPATH is set by PyInstaller)
PKG = os.path.join(ROOT, "bokin_suno")
datas = [(os.path.join(PKG, "static", "index.html"), os.path.join("bokin_suno", "static"))]
if os.path.exists(os.path.join(PKG, "version.txt")):
    datas.append((os.path.join(PKG, "version.txt"), "bokin_suno"))

a = Analysis(
    [os.path.join(SPECPATH, "bokin_suno_master.py")],  # noqa: F821
    pathex=[ROOT],
    # libsndfile (WAV, FLAC, MP3) and its licence come with soundfile, in _soundfile_data; truststore's
    # licence (MIT) with it (Windows' own certificate check: bokin_suno/updater.py)
    binaries=collect_dynamic_libs("_soundfile_data"),
    datas=datas + collect_data_files("_soundfile_data") + copy_metadata("truststore"),
    hiddenimports=collect_submodules("uvicorn") + ["_soundfile_data", "multipart", "python_multipart", "truststore",
                                                  "bokin_suno.selftest"],
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "PIL"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="BokinSunoMaster",
          icon=os.path.join(SPECPATH, "icon.ico"), console=False, upx=False)  # noqa: F821
coll = COLLECT(exe, a.binaries, a.datas, name="BokinSunoMaster", upx=False)
