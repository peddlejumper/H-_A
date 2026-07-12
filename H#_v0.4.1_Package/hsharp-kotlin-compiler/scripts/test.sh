#!/bin/sh
# Run the test suite
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# First, build the compiler if needed
if [ ! -f "build/libs/hsharp-kotlin-compiler.jar" ]; then
    ./scripts/build.sh
fi

# Find the kotlinc wrapper
if [ -x .kotlin/kotlinc.sh ]; then
    KOTLINC=".kotlin/kotlinc.sh"
else
    KOTLINC="$(command -v kotlinc || true)"
    if [ -z "$KOTLINC" ]; then
        echo "no kotlinc available"; exit 1
    fi
fi

# Compile tests
TEST_CLASSES="build/test-classes"
mkdir -p "$TEST_CLASSES"
CP="build/libs/hsharp-kotlin-compiler.jar:$(ls .kotlin/*.jar 2>/dev/null | tr '\n' ':')"
echo "[test.sh] compiling test sources..."
"$KOTLINC" -cp "$CP" -d "$TEST_CLASSES" -jvm-target 17 $(find src/test/kotlin -name '*.kt') || exit 1

# Run
echo "[test.sh] running tests..."
java -cp "$TEST_CLASSES:$CP" com.hsharp.compiler.CompilerTestsKt
