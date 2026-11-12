#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Hardware/LAN defaults. Override these variables for demo or local-only use.
export ROBOT_MODE="${ROBOT_MODE:-hardware}"
export ROBOT_HOST="${ROBOT_HOST:-0.0.0.0}"
export ROBOT_UDP_HOST="${ROBOT_UDP_HOST:-0.0.0.0}"
export ROBOT_ALLOW_UNLOCALIZED_CONTROL="${ROBOT_ALLOW_UNLOCALIZED_CONTROL-1}"
python="../.venv/bin/python"
if [[ ! -x "$python" ]]; then
  echo '请先在仓库根目录运行：uv sync --python 3.12 --extra test'
  exit 1
fi
if [[ ! -f frontend/dist/index.html ]]; then
  npm --prefix frontend ci
  npm --prefix frontend run build
fi
if [[ "${ROBOT_START_VISION:-1}" == 0 ]]; then
  exec "$python" -m backend.app
fi

vision_port="${ROBOT_VISION_PORT:-8765}"
"$python" -c 'import socket, sys; s = socket.socket(); s.bind(("127.0.0.1", int(sys.argv[1]))); s.close()' "$vision_port" || {
  echo "视觉服务端口 $vision_port 不可用，请设置 ROBOT_VISION_PORT 或使用 ROBOT_START_VISION=0。" >&2
  exit 1
}
export ROBOT_DEFAULT_VISION_URL="${ROBOT_DEFAULT_VISION_URL:-http://127.0.0.1:$vision_port}"
vision_args=(--port "$vision_port" --initial-source disconnected)
if [[ -n "${ROBOT_VISION_RUNTIME_CONFIG:-}" ]]; then
  vision_args+=(--runtime-config "$ROBOT_VISION_RUNTIME_CONFIG")
fi
"$python" ../apriltag_live.py "${vision_args[@]}" &
vision_pid=$!
backend_pid=""
cleanup() {
  trap - EXIT INT TERM
  [[ -z "$backend_pid" ]] || kill "$backend_pid" 2>/dev/null || true
  kill "$vision_pid" 2>/dev/null || true
  [[ -z "$backend_pid" ]] || wait "$backend_pid" 2>/dev/null || true
  wait "$vision_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
ready=0
for ((attempt=0; attempt<100; attempt++)); do
  if ! kill -0 "$vision_pid" 2>/dev/null; then
    echo '视觉服务启动失败。' >&2
    exit 1
  fi
  if curl --silent --fail --max-time 1 "http://127.0.0.1:$vision_port/api/config" >/dev/null; then
    ready=1
    break
  fi
  sleep 0.1
done
if [[ "$ready" != 1 ]]; then
  echo '视觉服务启动超时。' >&2
  exit 1
fi
"$python" -m backend.app &
backend_pid=$!
wait "$backend_pid"
