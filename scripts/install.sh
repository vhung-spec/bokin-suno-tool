#!/usr/bin/env bash
# One-step install of Bokin Suno Master on Linux or Windows (inside WSL2):
# system packages, Python env, the app and a desktop shortcut. Safe to run
# again (it skips what is already there).
#
#   git clone -b claude/suno-ai-mastering-tool-rfg0o5 https://github.com/vhung-spec/bokin-suno-tool.git ~/bokin-suno-tool
#   ~/bokin-suno-tool/scripts/install.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if command -v apt-get >/dev/null 2>&1; then
  missing=""
  # ffmpeg only reads formats libsndfile cannot (m4a, aac, opus)
  for pkg in python3-venv ffmpeg git; do
    dpkg -s "$pkg" >/dev/null 2>&1 || missing="$missing $pkg"
  done
  if [ -n "$missing" ]; then
    echo "== system packages:$missing (needs your password)"
    sudo apt-get update -qq
    # shellcheck disable=SC2086
    sudo apt-get install -y -qq $missing
  fi
fi

echo "== Python environment"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -e ".[app]"

echo "== shortcut"
if grep -qi microsoft /proc/version 2>/dev/null; then
  # A .bat on the Windows desktop that starts the app inside this WSL distro;
  # its console window shows the app's log, closing it stops the app.
  desktop_win="$(powershell.exe -NoProfile -Command '[Environment]::GetFolderPath("Desktop")' | tr -d '\r')"
  bat="$(wslpath -u "$desktop_win")/Bokin Suno Master.bat"
  distro_arg=""
  [ -n "${WSL_DISTRO_NAME:-}" ] && distro_arg="-d $WSL_DISTRO_NAME "
  printf '@echo off\r\ntitle Bokin Suno Master\r\nwsl.exe %s--cd "%s" -- ./.venv/bin/bokin-suno app\r\n' \
    "$distro_arg" "$ROOT" > "$bat"
  echo "Desktop shortcut: $desktop_win\\Bokin Suno Master.bat"
else
  apps="$HOME/.local/share/applications"
  mkdir -p "$apps"
  cat > "$apps/bokin-suno-master.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Bokin Suno Master
Exec=$ROOT/.venv/bin/bokin-suno app
Path=$ROOT
Terminal=true
Categories=AudioVideo;Audio;
EOF
  echo "Menu entry: $apps/bokin-suno-master.desktop"
fi

echo "Done. Start the app with the shortcut, or: $ROOT/.venv/bin/bokin-suno app"
