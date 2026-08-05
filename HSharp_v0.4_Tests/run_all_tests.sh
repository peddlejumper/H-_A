#!/bin/bash
# H# v0.4 — 运行所有测试
#
# 稳定性更新：测试始终从项目根目录运行，使用根目录下的权威核心文件
# (interpreter.py / parser.py / ...)，并通过入口文件目录祖先回溯解析
# import 路径，避免依赖陈旧的 HSharp_v0.4_Tests 副本。

set -e
# 脚本位于 HSharp_v0.4_Tests/，其父目录即项目根
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"

PASS=0
FAIL=0
TOTAL=0

run_test() {
    local name="$1"
    local rel="$2"
    local file="HSharp_v0.4_Tests/$rel"
    TOTAL=$((TOTAL + 1))
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  [$TOTAL] $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    local out
    if out=$($PY interpreter.py "$file" 2>&1); then
        if echo "$out" | grep -q "ALL TESTS PASSED\|All tests passed!\|Tests:.*Passed:.*Failed: 0\|Compiler chain OK!\|Interpreter chain OK!\|Done!"; then
            PASS=$((PASS + 1))
            echo "✅ $name"
        else
            FAIL=$((FAIL + 1))
            echo "❌ $name (no PASS marker)"
            echo "$out" | tail -5
        fi
    else
        FAIL=$((FAIL + 1))
        echo "❌ $name (crashed)"
        echo "$out" | tail -8
    fi
}

run_test "Union Types"        "bootstrap/test_union.hto"
run_test "zwui .NET"          "bootstrap/test_hwdui_dotnet.hto"
run_test "zwui Java"          "bootstrap/test_hwdui_java.hto"
run_test "zwui C++"           "bootstrap/test_hwdui_cpp.hto"
run_test "ML"                 "bootstrap/test_hsharpmyl.hto"
run_test "ML v4"              "bootstrap/test_hsharpmyl_v4.hto"
run_test "Standard Libs"      "bootstrap/test_standard_libs.hto"
run_test "Compiler Chain"     "bootstrap/test_compiler_chain.hto"
run_test "Interpreter Chain"  "bootstrap/test_interp_chain.hto"

echo ""
echo "═══════════════════════════════════════"
echo "  Total: $TOTAL | Pass: $PASS | Fail: $FAIL"
echo "═══════════════════════════════════════"
