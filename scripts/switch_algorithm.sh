#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <adaptive|random|round_robin>" >&2
  exit 1
fi

if [[ -z "${SELECTOR_BASE_URL:-}" ]]; then
  echo "SELECTOR_BASE_URL is required" >&2
  exit 1
fi

MODE="$1"
case "$MODE" in
  adaptive|random|round_robin)
    ;;
  *)
    echo "Unknown selector mode: $MODE" >&2
    exit 1
    ;;
esac

curl -k -fsS "${SELECTOR_BASE_URL%/}/admin/mode?value=${MODE}" >/dev/null

echo "Switched selector mode to: $MODE"
