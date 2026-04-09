#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

require_cmd gcloud
require_gcp_project

if [[ ! -d "$REPO_ROOT/dash-content/video" ]]; then
  echo "dash-content/video not found" >&2
  exit 1
fi

MANIFEST_PATH="${SELECTOR_MANIFEST_PATH:-/video/dash_content/clip1/manifest.mpd}"
SEGMENT_PATH="${SELECTOR_SEGMENT_PATH:-${SELECTOR_THROUGHPUT_PATH:-/video/dash_content/clip1/360p_dashinit.mp4}}"
LOCAL_MANIFEST="$REPO_ROOT/dash-content${MANIFEST_PATH}"
LOCAL_SEGMENT="$REPO_ROOT/dash-content${SEGMENT_PATH}"

if [[ ! -f "$LOCAL_MANIFEST" ]]; then
  echo "Required DASH manifest not found at $LOCAL_MANIFEST" >&2
  echo "Run dash-content/encode.sh first so deploy has real media to upload." >&2
  exit 1
fi

if [[ ! -f "$LOCAL_SEGMENT" ]]; then
  echo "Configured probe/test segment not found at $LOCAL_SEGMENT" >&2
  echo "Set SELECTOR_SEGMENT_PATH (or SELECTOR_THROUGHPUT_PATH) to a real segment path from your encoded assets." >&2
  exit 1
fi

if [[ -z "${ORIGIN_VMS:-}" ]]; then
  echo "ORIGIN_VMS env var is required" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [[ -n "${SELECTOR_VM:-}" || -n "${SELECTOR_ZONE:-}" ]]; then
  require_env SELECTOR_VM
  require_env SELECTOR_ZONE
  require_env SELECTOR_BASE_URL
  require_env ORIGIN_ENDPOINTS

  write_selector_config "$TMP_DIR/config.json"

  echo "Deploying selector service to $SELECTOR_VM ($SELECTOR_ZONE)"
  gssh "$SELECTOR_VM" "$SELECTOR_ZONE" "rm -rf ~/dash-selector && mkdir -p ~/dash-selector"
  gscp_to_recursive "$REPO_ROOT/selector" "$SELECTOR_VM" "$SELECTOR_ZONE" "~/dash-selector"
  gscp_to "$TMP_DIR/config.json" "$SELECTOR_VM" "$SELECTOR_ZONE" "~/dash-selector/config.json"
  gssh "$SELECTOR_VM" "$SELECTOR_ZONE" "sudo mkdir -p /opt/dash-selector /etc/dash-selector && sudo rm -rf /opt/dash-selector/selector && sudo cp -r ~/dash-selector/selector /opt/dash-selector/selector && sudo cp ~/dash-selector/config.json /etc/dash-selector/config.json && sudo systemctl restart dash-selector"
fi

for entry in ${ORIGIN_VMS//,/ }; do
  id="${entry%%:*}"
  rest="${entry#*:}"
  vm="${rest%%:*}"
  zone="${rest##*:}"

  echo "Deploying DASH content to $id ($vm / $zone)"
  gssh "$vm" "$zone" "rm -rf ~/dash-video && mkdir -p ~/dash-video"
  gscp_to_recursive "$REPO_ROOT/dash-content/video" "$vm" "$zone" "~/dash-video"
  gssh "$vm" "$zone" "sudo mkdir -p /var/www/dash && sudo rm -rf /var/www/dash/video && sudo cp -r ~/dash-video/video /var/www/dash/video && sudo chown -R www-data:www-data /var/www/dash/video && sudo systemctl restart nginx"
done

echo "Content deployment complete."
