#!/usr/bin/env bash
set -e
OUT=${1:-hsharp-0.4.hps}
# Exclude common heavy folders
EXCLUDES=(--exclude .git --exclude hsharp-ide/artifacts --exclude vscode-main/.git --exclude .vs --exclude "**/node_modules/*" --exclude "**/bin/*" --exclude "**/obj/*")

echo "Creating HPS package: $OUT"
zip -r "$OUT" . "${EXCLUDES[@]}"
echo "Created $OUT"
