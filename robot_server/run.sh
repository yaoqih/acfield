#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python="../.venv/bin/python"
if [[ ! -x "$python" ]]; then
  echo '请先在仓库根目录运行：uv sync --python 3.12 --extra test'
  exit 1
fi
if [[ ! -f frontend/dist/index.html ]]; then
  npm --prefix frontend ci
  npm --prefix frontend run build
fi
exec "$python" -m backend.app
