#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
docker_bin=${MANGA_DOCKER:-}
if [ -z "$docker_bin" ] && command -v docker >/dev/null 2>&1; then docker_bin=$(command -v docker); fi
if [ -z "$docker_bin" ] && [ -x "$HOME/.orbstack/bin/docker" ]; then docker_bin="$HOME/.orbstack/bin/docker"; fi
if [ -z "$docker_bin" ] && [ -x /Applications/OrbStack.app/Contents/MacOS/xbin/docker ]; then docker_bin=/Applications/OrbStack.app/Contents/MacOS/xbin/docker; fi
if [ -z "$docker_bin" ]; then echo 'Docker was not found.' >&2; exit 1; fi
case "${1:-status}" in
    start-openlist) "$docker_bin" compose up -d openlist ;;
    start)
        python3 scripts/fetch-release.py
        /bin/sh scripts/build-patches.sh
        "$docker_bin" compose up -d --build
        ;;
    stop) "$docker_bin" compose stop ;;
    status) "$docker_bin" compose ps ;;
    logs) "$docker_bin" compose logs --tail=80 "${2:-indexer}" ;;
    refresh)
        "$docker_bin" compose kill -s SIGHUP rclone
        "$docker_bin" compose exec -T indexer /bin/sh /scripts/run-index-once.sh manual
        ;;
    password) python3 scripts/setup.py --show-password ;;
    *) printf 'Usage: %s {start-openlist|start|stop|status|logs [service]|refresh|password}\n' "$0" >&2; exit 2 ;;
esac
