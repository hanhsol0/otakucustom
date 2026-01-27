#!/bin/bash
# Sync plugin source files from repo to Kodi addon directory
# Usage: ./sync-to-kodi.sh

SRC="/home/hdtra/projects/otakucustom/plugin.video.otaku.testing"
DST="/mnt/c/Users/hdtra/AppData/Roaming/Kodi/addons/plugin.video.otaku.testing"

rsync -av --delete \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  "$SRC/" "$DST/"

echo "Synced to Kodi addon directory"
