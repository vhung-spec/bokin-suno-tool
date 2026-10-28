"""Writes the app icon (packaging/brand: the "Su" tile of the Bokin family) into packaging/icon.ico.
Run before PyInstaller."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "brand"))
import make_icons  # noqa: E402

OUT = os.path.join(HERE, "icon.ico")

if __name__ == "__main__":
    print(make_icons.write_ico("suno-master", OUT))
