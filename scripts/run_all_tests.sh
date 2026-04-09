#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

if [[ -z "${SELECTOR_BASE_URL:-}" ]]; then
  echo "SELECTOR_BASE_URL is required, e.g. http://1.2.3.4" >&2
  exit 1
fi

DEGRADE_LATENCY_MS="${DEGRADE_LATENCY_MS:-100}"
DEGRADE_LOSS_PERCENT="${DEGRADE_LOSS_PERCENT:-2}"
OUT_DIR="${SCRIPT_DIR}/../new-results"
MODES=(adaptive random round_robin)

mkdir -p "$OUT_DIR"
echo "Output directory: $OUT_DIR"

# Determine whether degraded-condition tests are possible
CAN_DEGRADE=true
if [[ -z "${ORIGIN_VMS:-}" ]]; then
  echo "Warning: ORIGIN_VMS not set — skipping degraded-condition tests" >&2
  CAN_DEGRADE=false
fi
if [[ -z "${GCP_PROJECT:-}" ]]; then
  echo "Warning: GCP_PROJECT not set — skipping degraded-condition tests" >&2
  CAN_DEGRADE=false
fi

# Track the currently degraded server so we can clean up on error
CURRENT_DEGRADED_SERVER=""

cleanup_on_exit() {
  if [[ -n "$CURRENT_DEGRADED_SERVER" ]]; then
    echo "Cleaning up: resetting $CURRENT_DEGRADED_SERVER before exit..."
    "$SCRIPT_DIR/reset_network.sh" "$CURRENT_DEGRADED_SERVER" || true
  fi
}
trap cleanup_on_exit EXIT

# ── Phase 1: Baseline ────────────────────────────────────────────────────────
echo ""
echo "=== Phase 1: Baseline (no degradation) ==="
for mode in "${MODES[@]}"; do
  out="$OUT_DIR/${mode}_baseline.csv"
  echo "  Running mode=$mode -> $out"
  "$SCRIPT_DIR/run_tests.sh" "$out" "$mode"
done

# ── Phase 2: Degraded conditions ─────────────────────────────────────────────
if [[ "$CAN_DEGRADE" == "true" ]]; then
  # Parse server IDs from ORIGIN_VMS
  SERVER_IDS=()
  for entry in ${ORIGIN_VMS//,/ }; do
    SERVER_IDS+=("${entry%%:*}")
  done

  for server_id in "${SERVER_IDS[@]}"; do
    echo ""
    echo "=== Phase 2: Degrading $server_id (${DEGRADE_LATENCY_MS}ms, ${DEGRADE_LOSS_PERCENT}% loss) ==="

    CURRENT_DEGRADED_SERVER="$server_id"
    "$SCRIPT_DIR/simulate_network.sh" "$server_id" "$DEGRADE_LATENCY_MS" "$DEGRADE_LOSS_PERCENT"

    for mode in "${MODES[@]}"; do
      out="$OUT_DIR/${mode}_${server_id}_degraded.csv"
      echo "  Running mode=$mode -> $out"
      "$SCRIPT_DIR/run_tests.sh" "$out" "$mode"
    done

    echo "  Resetting $server_id..."
    "$SCRIPT_DIR/reset_network.sh" "$server_id"
    CURRENT_DEGRADED_SERVER=""
  done
fi

# ── Restore selector to adaptive ─────────────────────────────────────────────
echo ""
echo "=== Restoring selector mode to adaptive ==="
"$SCRIPT_DIR/switch_algorithm.sh" adaptive

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "=== Done. Output files ==="
ls -1 "$OUT_DIR"/*.csv 2>/dev/null || echo "  (no CSV files found)"
