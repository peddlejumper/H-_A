#!/bin/bash
# H# v0.4 — 运行所有测试

set -e
cd "$(dirname "$0")"

PASS=0
FAIL=0
TOTAL=0

run_test() {
    local name="$1"
    local file="$2"
    TOTAL=$((TOTAL + 1))
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  [$TOTAL] $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if python3 interpreter.py "$file" 2>&1 | tail -5; then
        if python3 interpreter.py "$file" 2>&1 | grep -q "ALL TESTS PASSED\|Tests:.*Passed:.*Failed: 0"; then
            PASS=$((PASS + 1))
            echo "✅ $name"
        else
            FAIL=$((FAIL + 1))
            echo "❌ $name (no PASS marker)"
        fi
    else
        FAIL=$((FAIL + 1))
        echo "❌ $name (crashed)"
    fi
}

run_test "Union Types" "bootstrap/test_union.hto"
run_test "zwui .NET" "bootstrap/test_hwdui_dotnet.hto"
run_test "zwui Java" "bootstrap/test_hwdui_java.hto"
run_test "zwui C++" "bootstrap/test_hwdui_cpp.hto"
run_test "ML" "bootstrap/test_hsharpmyl.hto"
run_test "ML v4" "bootstrap/test_hsharpmyl_v4.hto"
run_test "Standard Libs" "bootstrap/test_standard_libs.hto"
run_test "Compiler Chain" "bootstrap/test_compiler_chain.hto"
run_test "Interpreter Chain" "bootstrap/test_interp_chain.hto"

echo ""
echo "═══════════════════════════════════════"
echo "  Total: $TOTAL | Pass: $PASS | Fail: $FAIL"
echo "═══════════════════════════════════════"
