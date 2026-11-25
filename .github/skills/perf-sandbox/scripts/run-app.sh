#!/bin/bash
# Start SD.Next from a working copy on its own port and wait until the API answers.
#
# Usage: run-app.sh <copy> <port> [extra launch.py args]
#   Log: <copy>/tmp/server-<port>.log   PID file: <copy>/tmp/server-<port>.pid   Stop with: stop-app.sh <copy> <port>
# Env:   SD_MODELSDIR     models folder, the same variable launch.py reads (default: <main checkout>/models, shared by all copies)
#        OMP_NUM_THREADS  default 1; the loader then raises torch threads to half the cores, so several servers can share a machine
#        SD_MIN_FREE_MB   default 3000; wait until this much memory is available, give up after 20 minutes (Linux only)
# Exit codes: 0 ready, 1 server failed or timed out, 2 not enough memory.
WT="${1:?usage: run-app.sh <copy> <port> [launch.py args]}"; PORT="${2:?usage: run-app.sh <copy> <port> [launch.py args]}"; shift 2
WT="$(cd "$WT" && pwd)" || exit 1
COMMON="$(git -C "$WT" rev-parse --path-format=absolute --git-common-dir)" || exit 1
MAIN="$(dirname "$COMMON")"
PY="$WT/venv/bin/python"; [ -x "$PY" ] || PY="$MAIN/venv/bin/python"
MODELS="${SD_MODELSDIR:-$MAIN/models}"
cd "$WT" || exit 1
mkdir -p tmp
if [ -f "tmp/server-$PORT.pid" ]; then
  OLD="$(cat "tmp/server-$PORT.pid")"
  if ps -o args= -p "$OLD" 2>/dev/null | grep -Eq -- "launch\.py.* --port $PORT( |$)"; then echo "already running pid=$OLD"; exit 0; fi
  rm -f "tmp/server-$PORT.pid" # stale: the server died and the pid may belong to another process now
fi
if [ -r /proc/meminfo ]; then
  n=0
  while [ "$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)" -lt "${SD_MIN_FREE_MB:-3000}" ]; do
    if [ $n -ge 240 ]; then echo "memory guard: less than ${SD_MIN_FREE_MB:-3000} MB available for 20 minutes, not starting"; exit 2; fi
    sleep 5; n=$((n+1))
  done
fi
ROOTFLAG=""; [ "$(id -u)" = "0" ] && ROOTFLAG="-f"
OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}" nohup "$PY" launch.py $ROOTFLAG --port "$PORT" --models-dir "$MODELS" "$@" > "tmp/server-$PORT.log" 2>&1 &
PID=$!
echo "$PID" > "tmp/server-$PORT.pid"
for _ in $(seq 1 300); do
  if curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$PORT/sdapi/v1/version"; then echo "ready pid=$PID port=$PORT log=$WT/tmp/server-$PORT.log"; exit 0; fi
  if ! kill -0 "$PID" 2>/dev/null; then echo "server exited early, last log lines:"; tail -40 "tmp/server-$PORT.log"; rm -f "tmp/server-$PORT.pid"; exit 1; fi
  sleep 1
done
echo "timeout waiting for server, last log lines:"; tail -40 "tmp/server-$PORT.log"; exit 1
