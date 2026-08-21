#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-status}"
HUB_DIR="${HUB:-${CODEX_HOME:-}}"

if [[ -z "${HUB_DIR}" ]]; then
  if [[ -d "${HOME}/.codex/token-telemetry" ]]; then
    HUB_DIR="${HOME}/.codex"
  elif [[ -d "${HOME}/.cursor/token-telemetry" ]]; then
    HUB_DIR="${HOME}/.cursor"
  elif [[ -d "${HOME}/.gemini/antigravity/token-telemetry" ]]; then
    HUB_DIR="${HOME}/.gemini/antigravity"
  else
    HUB_DIR="${HOME}/.codex"
  fi
fi

TT_DIR="${HUB_DIR}/token-telemetry"
PID_FILE="${TT_DIR}/dashboard.pid"
LOG_FILE="${TT_DIR}/dashboard.log"
APP="${TT_DIR}/serve_dashboard.py"
VENV_PY="${TT_DIR}/.venv-desktop/bin/python"
COMPRESSION_ENV="${HUB_DIR}/compression.env"

if [[ -f "${COMPRESSION_ENV}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${COMPRESSION_ENV}"
  set +a
fi

if [[ -x "${VENV_PY}" ]]; then
  PYTHON_BIN="${VENV_PY}"
else
  PYTHON_BIN="python3"
fi

is_running() {
  [[ -f "${PID_FILE}" ]] && kill -0 "$(cat "${PID_FILE}")" 2>/dev/null
}

find_app_pid() {
  pgrep -f "${APP}" 2>/dev/null | head -n 1 || true
}

status_dashboard() {
  if is_running; then
    echo "S.C.R.O.O.G.E dashboard running: PID $(cat "${PID_FILE}")"
  elif pid="$(find_app_pid)" && [[ -n "${pid}" ]]; then
    echo "${pid}" > "${PID_FILE}"
    echo "S.C.R.O.O.G.E dashboard running: PID ${pid} (PID file restored)"
  else
    echo "S.C.R.O.O.G.E dashboard not running for HUB=${HUB_DIR}"
    return 1
  fi
}

start_dashboard() {
  if is_running; then
    status_dashboard
    return 0
  fi
  mkdir -p "${TT_DIR}"
  if command -v setsid >/dev/null 2>&1; then
    PYTHONUNBUFFERED=1 setsid "${PYTHON_BIN}" "${APP}" >> "${LOG_FILE}" 2>&1 &
  else
    PYTHONUNBUFFERED=1 nohup "${PYTHON_BIN}" "${APP}" >> "${LOG_FILE}" 2>&1 &
  fi
  echo "$!" > "${PID_FILE}"
  sleep 0.5
  url="$(grep -Eo 'http://[^ ]+' "${LOG_FILE}" 2>/dev/null | tail -n 1 || true)"
  if [[ -n "${url}" ]]; then
    echo "S.C.R.O.O.G.E dashboard started: PID $(cat "${PID_FILE}") -> ${url}"
  else
    echo "S.C.R.O.O.G.E dashboard started: PID $(cat "${PID_FILE}") (see ${LOG_FILE} for URL)"
  fi
}

stop_dashboard() {
  pid=""
  if is_running; then
    pid="$(cat "${PID_FILE}")"
  else
    pid="$(find_app_pid)"
  fi

  if [[ -n "${pid}" ]]; then
    kill "${pid}"
    for _ in 1 2 3 4 5; do
      if ! kill -0 "${pid}" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done
    if kill -0 "${pid}" 2>/dev/null; then
      echo "Dashboard PID ${pid} did not stop after SIGTERM; use: kill -9 ${pid}"
      return 1
    fi
    rm -f "${PID_FILE}"
    echo "S.C.R.O.O.G.E dashboard stopped: PID ${pid}"
    return 0
  fi

  rm -f "${PID_FILE}"
  echo "No running dashboard found for HUB=${HUB_DIR}"
}

case "${ACTION}" in
  start)
    start_dashboard
    ;;
  stop)
    stop_dashboard
    ;;
  restart)
    stop_dashboard || true
    start_dashboard
    ;;
  status)
    status_dashboard
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
