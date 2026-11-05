#!/usr/bin/env bash
set -euo pipefail

# Start the real-device backend on all local network interfaces.
export ROBOT_MODE=hardware
export ROBOT_HOST="${ROBOT_HOST:-0.0.0.0}"
export ROBOT_UDP_HOST="${ROBOT_UDP_HOST:-0.0.0.0}"
export ROBOT_START_VISION="${ROBOT_START_VISION:-1}"

exec "$(dirname "$0")/run.sh"
