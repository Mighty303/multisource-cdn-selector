#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${SELECTOR_BASE_URL:-}" ]]; then
  echo "SELECTOR_BASE_URL is required, e.g. http://1.2.3.4" >&2
  exit 1
fi

MANIFEST_PATH="${SELECTOR_MANIFEST_PATH:-/video/dash_content/clip1/manifest.mpd}"
MPD_URL="${SELECTOR_BASE_URL%/}${MANIFEST_PATH}"
SEGMENT_PATH="${SELECTOR_SEGMENT_PATH:-${SELECTOR_THROUGHPUT_PATH:-/video/dash_content/clip1/360p_dashinit.mp4}}"
SEG_URL="${SELECTOR_BASE_URL%/}${SEGMENT_PATH}"
OUT_FILE="${1:-results/load_test_results.csv}"
MODE_FILTER="${2:-all}"
mkdir -p "$(dirname "$OUT_FILE")"
echo "mode,clients,http_code,time_total,url_effective" > "$OUT_FILE"

case "$MODE_FILTER" in
  all|adaptive|random|round_robin)
    ;;
  *)
    echo "Usage: $0 [output_csv] [all|adaptive|random|round_robin]" >&2
    exit 1
    ;;
esac

echo "Checking MPD availability"
curl -k -f -sS "$MPD_URL" >/dev/null

echo "Checking segment availability"
curl -k -f -L -sS "$SEG_URL" >/dev/null

if [[ "$MODE_FILTER" == "all" ]]; then
  MODES=(adaptive random round_robin)
  echo "Running per-mode concurrent segment load tests"
else
  MODES=("$MODE_FILTER")
  echo "Running concurrent segment load test for mode=$MODE_FILTER"
fi

for mode in "${MODES[@]}"; do
  "$SCRIPT_DIR/switch_algorithm.sh" "$mode"
  for clients in 1 5 10; do
    echo "Mode=$mode Clients=$clients"
    seq "$clients" | xargs -I{} -P "$clients" curl -k -L -sS -o /dev/null -w "$mode,$clients,%{http_code},%{time_total},%{url_effective}\n" "$SEG_URL" >> "$OUT_FILE"
  done
done

echo "run_tests complete -> $OUT_FILE"
