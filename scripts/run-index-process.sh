#!/bin/sh
set -u
child=
terminate() {
    trap - TERM INT
    if [ -n "$child" ]; then
        # The scan is started in its own session, so this signals its entire
        # process group, including any per-directory timeout/ls children.
        kill -TERM "-$child" 2>/dev/null || kill -TERM "$child" 2>/dev/null || true
        sleep 1
        kill -KILL "-$child" 2>/dev/null || kill -KILL "$child" 2>/dev/null || true
        wait "$child" 2>/dev/null || true
    fi
    exit 124
}
trap terminate TERM INT
setsid /bin/sh /scripts/refresh-library.sh &
child=$!
wait "$child"
