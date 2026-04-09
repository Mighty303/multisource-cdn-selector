#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SELECTOR_BASE_URL:-}" ]]; then
  echo "Set SELECTOR_BASE_URL first" >&2
  exit 1
fi

MANIFEST_PATH="${SELECTOR_MANIFEST_PATH:-/video/dash_content/clip1/manifest.mpd}"
SEGMENT_PATH="${SELECTOR_SEGMENT_PATH:-${SELECTOR_THROUGHPUT_PATH:-/video/dash_content/clip1/360p_dashinit.mp4}}"

for path in /health "$MANIFEST_PATH"; do
  code=$(curl -k -s -o /dev/null -w "%{http_code}" "${SELECTOR_BASE_URL%/}${path}")
  if [[ "$code" != "200" ]]; then
    echo "FAIL ${path}: HTTP $code"
    exit 1
  fi
  echo "OK ${path}"
done

redirect_target=$(curl -k -sS -D - -o /dev/null "${SELECTOR_BASE_URL%/}${SEGMENT_PATH}" | tr -d '\r' | awk 'tolower($1)=="location:" {print $2}')
if [[ -z "$redirect_target" ]]; then
  echo "FAIL ${SEGMENT_PATH}: missing redirect location"
  exit 1
fi

curl -k -f -L -sS "${SELECTOR_BASE_URL%/}${SEGMENT_PATH}" >/dev/null
echo "OK ${SEGMENT_PATH} -> $redirect_target"
