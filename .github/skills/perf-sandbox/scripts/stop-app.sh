#!/bin/bash
# Stop a server started with run-app.sh.
# Usage: stop-app.sh <copy> <port>
#        stop-app.sh --all [<copies folder>]   stop every server that run-app.sh started in any copy (default folder: <parent of the main checkout>/wt)
stop_one() {
  f="$1/tmp/server-$2.pid"
  [ -f "$f" ] || { echo "no pid file: $f"; return 0; }
  PID=$(cat "$f")
  kill "$PID" 2>/dev/null
  for _ in $(seq 1 20); do kill -0 "$PID" 2>/dev/null || break; sleep 0.5; done
  kill -9 "$PID" 2>/dev/null
  rm -f "$f"
  echo "stopped pid=$PID port=$2 copy=$1"
}
if [ "${1:-}" = "--all" ]; then
  HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  MAIN="$(dirname "$(git -C "$HERE" rev-parse --path-format=absolute --git-common-dir)")"
  ROOT="${2:-${SD_WT_ROOT:-$(dirname "$MAIN")/wt}}"
  for f in "$ROOT"/*/tmp/server-*.pid; do
    [ -f "$f" ] || continue
    copy="$(dirname "$(dirname "$f")")"; port="$(basename "$f" .pid)"; port="${port#server-}"
    stop_one "$copy" "$port"
  done
  exit 0
fi
stop_one "${1:?usage: stop-app.sh <copy> <port> | --all}" "${2:?usage: stop-app.sh <copy> <port>}"
