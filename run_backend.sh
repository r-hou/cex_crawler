#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

LOG_DIR="$DIR/logs"
PID_FILE="$DIR/backend.pid"

# Config (override via env vars)
PYTHON_BIN="${PYTHON_BIN:-python3}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8888}"
APP_MODULE="${APP_MODULE:-backend:app}"

mkdir -p "$LOG_DIR"

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && ps -p "${pid}" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

start() {
  if is_running; then
    echo "backend is already running (pid $(cat "$PID_FILE"))"
    exit 0
  fi

  if [[ ! -f "$DIR/backend.py" ]]; then
    echo "backend.py not found in $DIR" >&2
    exit 1
  fi

  local cmd
  cmd=("$PYTHON_BIN" -m uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT")
  echo "Starting backend: ${cmd[*]}"
  nohup "${cmd[@]}" >> "$LOG_DIR/backend.out" 2>&1 &
  echo $! > "$PID_FILE"
  sleep 0.5
  if is_running; then
    echo "backend started (pid $(cat "$PID_FILE")), logs: $LOG_DIR/backend.out"
  else
    echo "backend failed to start, see logs: $LOG_DIR/backend.out" >&2
    exit 1
  fi
}

stop() {
  if ! is_running; then
    echo "backend is not running"
    rm -f "$PID_FILE"
    exit 0
  fi
  local pid
  pid="$(cat "$PID_FILE")"
  echo "Stopping backend (pid $pid)"
  kill "$pid" 2>/dev/null || true
  for _ in {1..20}; do
    if ! ps -p "$pid" >/dev/null 2>&1; then
      rm -f "$PID_FILE"
      echo "backend stopped"
      return 0
    fi
    sleep 0.2
  done
  echo "Force killing backend (pid $pid)"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
}

status() {
  if is_running; then
    echo "backend is running (pid $(cat "$PID_FILE"))"
  else
    echo "backend is not running"
  fi
}

restart() {
  stop || true
  start
}

logs() {
  tail -f "$LOG_DIR/backend.out"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) restart ;;
  status) status ;;
  logs) logs ;;
  *)
    echo "Usage: $0 {start|stop|restart|status|logs}"
    exit 1
    ;;
esac


