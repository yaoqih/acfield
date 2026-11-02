#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo '请先运行：uv sync --extra test，或按 README 创建 .venv。'
  exit 1
fi
if [[ ! -f frontend/dist/index.html ]]; then
  npm --prefix frontend ci
  npm --prefix frontend run build
fi
exec .venv/bin/python -m backend.app
