#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# package_hsharp.sh — 干净打包当前版本 H# 为 .hps 文件
# 只包含必要的运行时文件，排除 __pycache__、测试、IDE 等
# 用法: bash scripts/package_hsharp.sh [output_name]
# ═══════════════════════════════════════════════════════════════════════════
set -e

cd "$(dirname "$0")/.."
ROOT=$(pwd)
OUT="${1:-hsharp-0.4.hps}"

echo "═══ H# .hps Package Builder ═══"
echo "Output: $OUT"
echo ""

# ── Python 核心文件 ──
PY_FILES=(
    hsharp.py
    lexer.py
    parser.py
    interpreter.py
    compiler.py
    ast.py
    bytecode.py
    tokens.py
    h_ast.py
    host_functions.py
)

# ── Bootstrap H# 自举文件 ──
BTP_FILES=(
    bootstrap/interpreter.hto
    bootstrap/compiler.hto
    bootstrap/executor.hto
    bootstrap/parser.hto
    bootstrap/bootstrap.hto
    bootstrap/tokenize.hto
    bootstrap/hwdui.hto
    bootstrap/formatter.hto
    bootstrap/linter.hto
    bootstrap/fs_module.hto
    bootstrap/io_module.hto
    bootstrap/net_module.hto
    bootstrap/db_module.hto
    bootstrap/crypto_module.hto
    bootstrap/datetime_module.hto
    bootstrap/math_utils.hto
    bootstrap/math_extended.hto
    bootstrap/string_utils.hto
    bootstrap/array_utils.hto
    bootstrap/d3system.hto
    bootstrap/d3system_ops.hto
    bootstrap/perf_monitor.hto
    bootstrap/env_optimized.hto
    bootstrap/pkg_inspect.hto
)

# ── 清理旧文件 ──
rm -f "$OUT"

# ── 打包文件列表 ──
TMP_LIST=$(mktemp)

echo "package.json" >> "$TMP_LIST"

for f in "${PY_FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "$f" >> "$TMP_LIST"
        echo "  + $f"
    else
        echo "  ! SKIP (not found): $f"
    fi
done

for f in "${BTP_FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "$f" >> "$TMP_LIST"
        echo "  + $f"
    else
        echo "  ! SKIP (not found): $f"
    fi
done

# ── 创建 ZIP ──
FILE_COUNT=$(wc -l < "$TMP_LIST" | tr -d ' ')
echo ""
echo "Packaging $FILE_COUNT files into $OUT ..."

zip -q "$OUT" -@ < "$TMP_LIST"
rm -f "$TMP_LIST"

SIZE=$(du -h "$OUT" | cut -f1)
echo ""
echo "Done: $OUT ($SIZE)"
echo "Files: $FILE_COUNT"