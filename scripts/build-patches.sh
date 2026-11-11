#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ -z "${JDK_BIN:-}" ]; then
    if [ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/javac" ]; then
        JDK_BIN="$JAVA_HOME/bin"
    elif [ -x /opt/homebrew/opt/openjdk@17/bin/javac ]; then
        JDK_BIN=/opt/homebrew/opt/openjdk@17/bin
    elif [ -x /usr/local/opt/openjdk@17/bin/javac ]; then
        JDK_BIN=/usr/local/opt/openjdk@17/bin
    elif command -v javac >/dev/null 2>&1; then
        JDK_BIN=$(dirname "$(command -v javac)")
    else
        echo 'A JDK with javac (17 or newer) is required; set JDK_BIN to its bin directory.' >&2
        exit 1
    fi
fi
if [ ! -x "$JDK_BIN/java" ] || ! "$JDK_BIN/javac" -version >/dev/null 2>&1; then
    echo 'The selected JDK is not usable; set JDK_BIN to a working JDK bin directory.' >&2
    exit 1
fi
export JDK_BIN
python3 build/suwayomi/rarfix/build.py
python3 build/suwayomi/rarfix/build-cachefix.py
