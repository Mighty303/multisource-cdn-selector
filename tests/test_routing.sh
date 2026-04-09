#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${SELECTOR_BASE_URL:-}" ]]; then
  echo "Set SELECTOR_BASE_URL first" >&2
  exit 1
fi

if [[ -z "${ORIGIN_ENDPOINTS:-}" ]]; then
  echo "Set ORIGIN_ENDPOINTS first" >&2
  exit 1
fi

SEGMENT_PATH="${SELECTOR_SEGMENT_PATH:-${SELECTOR_THROUGHPUT_PATH:-/video/dash_content/clip1/360p_dashinit.mp4}}"

expected_endpoints=()
for entry in ${ORIGIN_ENDPOINTS//,/ }; do
  expected_endpoints+=("${entry#*:}")
done

"$SCRIPT_DIR/../scripts/switch_algorithm.sh" round_robin

for index in "${!expected_endpoints[@]}"; do
  redirect=$(curl -k -sS -D - -o /dev/null "${SELECTOR_BASE_URL%/}${SEGMENT_PATH}?rr=$index" | tr -d '\r' | awk 'tolower($1)=="location:" {print $2}')
  if [[ "$redirect" != "${expected_endpoints[$index]%/}${SEGMENT_PATH}"* ]]; then
    echo "FAIL round_robin step $index: expected ${expected_endpoints[$index]}, got $redirect"
    exit 1
  fi
  echo "OK round_robin step $index -> $redirect"
done

"$SCRIPT_DIR/../scripts/switch_algorithm.sh" adaptive
status_payload=$(curl -k -sS "${SELECTOR_BASE_URL%/}/api/status")
if ! grep -q '"mode": "adaptive"' <<<"$status_payload"; then
  echo "FAIL adaptive mode status check"
  exit 1
fi

echo "Selector routing smoke test complete"
