#!/bin/sh
# ============================================================
# build.sh - portable build for the h# kotlin-compiler
# ============================================================
#
# Produces:
#   build/libs/hsharp-kotlin-compiler.jar     (CLI tool)
#   build/libs/hsharp-runtime.jar             (standalone runtime)
#
# Requirements: Java 11+ on PATH.
# If kotlinc is not installed, the script downloads the necessary jars from
# Maven Central (one-time, cached in .kotlin/).
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# --- pick the kotlinc binary
KOTLINC="${KOTLINC:-}"
if [ -z "$KOTLINC" ] && command -v kotlinc >/dev/null 2>&1; then
    KOTLINC="$(command -v kotlinc)"
fi

KOTLIN_CACHE="$PROJECT_DIR/.kotlin"
KOTLIN_VERSION="${KOTLIN_VERSION:-2.0.21}"
COROUTINES_VERSION="${COROUTINES_VERSION:-1.7.3}"

if [ -z "$KOTLINC" ]; then
    echo "[build.sh] kotlinc not on PATH — using bundled jars in $KOTLIN_CACHE"
    mkdir -p "$KOTLIN_CACHE"
    download_jar() {
        art="$1"; ver="$2"
        jar="$KOTLIN_CACHE/$art-$ver.jar"
        if [ ! -f "$jar" ]; then
            echo "[build.sh] downloading $art:$ver"
            curl -L --max-time 120 --fail --silent --show-error -o "$jar" \
                "https://repo1.maven.org/maven2/org/jetbrains/kotlin/$art/$ver/$art-$ver.jar"
        fi
    }
    download_jar "kotlin-stdlib"             "$KOTLIN_VERSION"
    download_jar "kotlin-reflect"            "$KOTLIN_VERSION"
    download_jar "kotlin-script-runtime"     "$KOTLIN_VERSION"
    download_jar "kotlin-daemon-embeddable"  "$KOTLIN_VERSION"
    download_jar "kotlin-compiler-embeddable" "$KOTLIN_VERSION"
    # coroutines
    if [ ! -f "$KOTLIN_CACHE/kotlinx-coroutines-core-jvm-$COROUTINES_VERSION.jar" ]; then
        echo "[build.sh] downloading kotlinx-coroutines-core-jvm:$COROUTINES_VERSION"
        curl -L --max-time 120 --fail --silent --show-error \
            -o "$KOTLIN_CACHE/kotlinx-coroutines-core-jvm-$COROUTINES_VERSION.jar" \
            "https://repo1.maven.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-core-jvm/$COROUTINES_VERSION/kotlinx-coroutines-core-jvm-$COROUTINES_VERSION.jar"
    fi
    # Wrapper script
    KOTLINC="$KOTLIN_CACHE/kotlinc.sh"
    cat > "$KOTLINC" <<'WRAP'
#!/bin/sh
JAR_DIR="$(cd "$(dirname "$0")" && pwd)"
CP=$(ls "$JAR_DIR"/*.jar | tr '\n' ':')
exec java -cp "$CP" org.jetbrains.kotlin.cli.jvm.K2JVMCompiler "$@"
WRAP
    chmod +x "$KOTLINC"
fi
echo "[build.sh] using kotlinc: $KOTLINC"
"$KOTLINC" -version 2>&1 | tail -1 || true

# --- locate java
if [ -z "${JAVA:-}" ]; then
    JAVA="$(command -v java || true)"
    if [ -z "$JAVA" ]; then
        echo "[build.sh] no 'java' in PATH" >&2; exit 1
    fi
fi

# --- compile
BUILD_DIR="$PROJECT_DIR/build"
CLASSES_DIR="$BUILD_DIR/classes"
LIBS_DIR="$BUILD_DIR/libs"
mkdir -p "$CLASSES_DIR" "$LIBS_DIR"

SRC_FILES=$(find src/main/kotlin -name '*.kt')
echo "[build.sh] compiling $(echo "$SRC_FILES" | wc -l | tr -d ' ') source files..."
"$KOTLINC" -d "$CLASSES_DIR" -jvm-target 17 -classpath "$(ls "$KOTLIN_CACHE"/*.jar 2>/dev/null | tr '\n' ':')" $SRC_FILES

# --- runtime jar  (the small launcher that ships in the app)
# We *unpack* kotlin-stdlib into the classes dir before jarring so the
# runtime jar is fully self-contained (no Class-Path, works under jpackage).
echo "[build.sh] repackaging kotlin-stdlib into runtime jar"
STD_JAR="$KOTLIN_CACHE/kotlin-stdlib-2.0.21.jar"
if [ -f "$STD_JAR" ]; then
    ( cd "$CLASSES_DIR" && jar xf "$STD_JAR" )
    # Remove the META-INF/versions duplicate signature files
    rm -rf "$CLASSES_DIR/META-INF/versions" 2>/dev/null || true
    rm -f "$CLASSES_DIR/META-INF/MANIFEST.MF" 2>/dev/null || true
fi
COR_JAR="$KOTLIN_CACHE/kotlinx-coroutines-core-jvm-1.7.3.jar"
if [ -f "$COR_JAR" ]; then
    ( cd "$CLASSES_DIR" && jar xf "$COR_JAR" )
    rm -rf "$CLASSES_DIR/META-INF/versions" 2>/dev/null || true
fi
RTMF="$BUILD_DIR/RUNTIME_MANIFEST.MF"
printf "Manifest-Version: 1.0\nMain-Class: com.hsharp.runtime.HbcLauncher\n" > "$RTMF"
( cd "$CLASSES_DIR" && jar cfm "$LIBS_DIR/hsharp-runtime.jar" "$RTMF" . )
echo "[build.sh] built $LIBS_DIR/hsharp-runtime.jar"

# --- compiler jar (the CLI tool)
# The compiler jar has the same fat layout so it can be run from anywhere.
CLIMF="$BUILD_DIR/CLI_MANIFEST.MF"
printf "Manifest-Version: 1.0\nMain-Class: com.hsharp.compiler.MainKt\n" > "$CLIMF"
( cd "$CLASSES_DIR" && jar cfm "$LIBS_DIR/hsharp-kotlin-compiler.jar" "$CLIMF" . )
echo "[build.sh] built $LIBS_DIR/hsharp-kotlin-compiler.jar"

# --- ship kotlin-stdlib inside the runtime jar's lib/ dir for the app
mkdir -p "$LIBS_DIR/lib"
if [ -d "$KOTLIN_CACHE" ]; then
    cp "$KOTLIN_CACHE"/kotlin-stdlib-*.jar             "$LIBS_DIR/lib/" 2>/dev/null || true
    cp "$KOTLIN_CACHE"/kotlinx-coroutines-core-jvm-*.jar "$LIBS_DIR/lib/" 2>/dev/null || true
fi

# --- ship the runtime jar INSIDE the compiler jar so the compiler can find
#     it no matter where the user puts it. The runtime lives at
#     lib/hsharp-runtime.jar inside the compiler jar; locateRuntimeJar()
#     extracts it on demand the first time the compiler is asked to package.
# Build order matters: we first finish the runtime jar, then bundle it
# into the compiler jar.
echo "[build.sh] embedding hsharp-runtime.jar into hsharp-kotlin-compiler.jar/lib/"
mkdir -p "$CLASSES_DIR/lib"
cp "$LIBS_DIR/hsharp-runtime.jar" "$CLASSES_DIR/lib/hsharp-runtime.jar"
( cd "$CLASSES_DIR" && jar cfm "$LIBS_DIR/hsharp-kotlin-compiler.jar" "$CLIMF" . )

echo
echo "[build.sh] DONE"
echo "  CLI:        java -jar $LIBS_DIR/hsharp-kotlin-compiler.jar <command> [args...]"
echo "  Run .hbc :  java -jar $LIBS_DIR/hsharp-runtime.jar <file.hbc>"
echo "  Example:    java -jar $LIBS_DIR/hsharp-kotlin-compiler.jar info ../bootstrap/test_simple.hbc"
