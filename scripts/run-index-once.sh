#!/bin/sh
set -eu
remote=${MANGA_REMOTE:-/remote}
mode=${1:-scheduled}
scan_timeout=${INDEX_SCAN_TIMEOUT_SECONDS:-900}
case "$scan_timeout" in *[!0-9]*|''|0) echo 'Invalid scan timeout' >&2; exit 1;; esac

# Both manual and scheduled scans run in this container and share this lock.
exec 9>/tmp/manga-index.lock
if [ "$mode" = manual ]; then
    if ! timeout 120 flock -x 9; then
        printf '%s index: timed out waiting for another scan\n' "$(date -u '+%FT%TZ')" >&2
        exit 1
    fi
else
    if ! flock -n -x 9; then
        printf '%s index: another scan is running; skipped\n' "$(date -u '+%FT%TZ')"
        exit 75
    fi
fi

printf '%s index: scan started\n' "$(date -u '+%FT%TZ')"
if ! timeout 45 ls -a "$remote" >/dev/null; then
    printf '%s index: cannot list manga mount\n' "$(date -u '+%FT%TZ')" >&2
    exit 1
fi
if ! timeout -k 5 "$scan_timeout" /bin/sh /scripts/run-index-process.sh; then
    printf '%s index: scan failed or timed out\n' "$(date -u '+%FT%TZ')" >&2
    exit 1
fi
date +%s > /tmp/manga-index-last-success
printf '%s index: scan completed\n' "$(date -u '+%FT%TZ')"
