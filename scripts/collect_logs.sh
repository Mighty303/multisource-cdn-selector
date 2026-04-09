#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

require_cmd gcloud
require_gcp_project

if [[ -z "${SELECTOR_VM:-}" || -z "${SELECTOR_ZONE:-}" ]]; then
  echo "SELECTOR_VM and SELECTOR_ZONE env vars are required" >&2
  exit 1
fi

OUT_PATH="${1:-results/selector.log}"
mkdir -p "$(dirname "$OUT_PATH")"

gssh "$SELECTOR_VM" "$SELECTOR_ZONE" "sudo tail -n 5000 /var/log/dash-selector/requests.log" > "$OUT_PATH"

echo "Wrote logs to $OUT_PATH"
