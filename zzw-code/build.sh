#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP_DIR="/tmp/zzw-code-build"

echo "🛠️  Building ZZW Code..."
echo "    Project: $PROJECT_DIR"

rm -rf "$TMP_DIR"
cp -r "$PROJECT_DIR" "$TMP_DIR"

cd "$TMP_DIR"

export PATH="/tmp/node/bin:$PATH"

node -e "require('vite').build({})"

rm -rf "$PROJECT_DIR/dist"
cp -r "$TMP_DIR/dist" "$PROJECT_DIR/dist"

rm -rf "$TMP_DIR"

echo "✅ Build complete! Output in $PROJECT_DIR/dist/"