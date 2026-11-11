#!/bin/sh
set -u
interval=${INDEX_INTERVAL_SECONDS:-3600}
retry=${INDEX_RETRY_SECONDS:-300}
case "$interval:$retry" in *[!0-9:]*|:*|*:|0:*|*:0) echo 'Invalid index interval' >&2; exit 1;; esac
retry_delay=$retry
trap 'exit 0' TERM INT
while :; do
    if /bin/sh /scripts/run-index-once.sh scheduled; then
        delay=$interval
        retry_delay=$retry
    else
        result=$?
        if [ "$result" -eq 75 ]; then
            delay=60
        else
            delay=$retry_delay
            retry_delay=$((retry_delay * 2))
            [ "$retry_delay" -le 3600 ] || retry_delay=3600
        fi
        printf '%s index: retrying in %s seconds\n' "$(date -u '+%FT%TZ')" "$delay" >&2
    fi
    sleep "$delay" &
    wait "$!" || exit 0
done
