#!/bin/bash
# Run all match stress tests on both Python VM (root hsharp.py) and Kotlin HVM.
cd /Users/peddlejumper/H#/v0.4 || exit 1
WD=stress_test/11_match
COMPILER=HSharp_v0.4_Tests/compile_test.py
JAR=hsharp-kotlin-compiler/build/libs/hsharp-kotlin-compiler.jar

for hto in "$WD"/t*.hto; do
    base=$(basename "$hto" .hto)
    echo "════════════════════════════════════════"
    echo "TEST: $base"
    echo "────────────────────────────────────────"
    echo "--- Python VM (root hsharp.py) ---"
    python3 hsharp.py "$hto" 2>&1 | head -n 5
    echo "--- Python VM (HSharp_v0.4_Tests interpreter) ---"
    (cd HSharp_v0.4_Tests && python3 interpreter.py "../$hto" 2>&1 | head -n 5)
    echo "--- Kotlin HVM ---"
    python3 "$COMPILER" "$hto" "$WD/$base.hbc" 2>&1 | tail -n 1
    java -jar "$JAR" run "$WD/$base.hbc" 2>&1
    echo ""
done
