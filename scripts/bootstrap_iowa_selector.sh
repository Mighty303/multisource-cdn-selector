#!/usr/bin/env bash
# bootstrap_iowa_selector.sh — Provision the DASH selector service on a GCP VM
# in Iowa (us-central1-a) and deploy the Python routing server.
#
# Usage:
#   bash scripts/bootstrap_iowa_selector.sh <key.json> [vm-name] [zone]
#
# Examples:
#   bash scripts/bootstrap_iowa_selector.sh key.json
#   bash scripts/bootstrap_iowa_selector.sh key.json dash-selector-iowa us-central1-a
#
# Required env:
#   ORIGIN_ENDPOINTS  — e.g. "oregon:http://10.0.0.10,toronto:http://10.0.1.10,ncalifornia:http://10.0.2.10"
#
# Optional env (selector tuning — see scripts/env.example):
#   SELECTOR_MODE, SELECTOR_WEIGHT_LATENCY, SELECTOR_WEIGHT_LOAD,
#   SELECTOR_WEIGHT_THROUGHPUT, SELECTOR_PROBE_TIMEOUT_SECONDS, SELECTOR_PROBE_TTL_SECONDS
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <key.json> [vm-name] [zone]" >&2
  exit 1
fi

KEY_FILE="$(realpath "$1")"
VM_NAME="${2:-dash-selector-iowa}"
ZONE="${3:-us-central1-a}"
SELECTOR_PORT=80

require_cmd gcloud
require_cmd python3
require_env ORIGIN_ENDPOINTS

if [[ ! -f "$KEY_FILE" ]]; then
  echo "Key file not found: $KEY_FILE" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Authenticate and extract project from key.json
# ---------------------------------------------------------------------------
echo "==> Activating service account from $KEY_FILE..."
gcloud auth activate-service-account --key-file="$KEY_FILE"

GCP_PROJECT="$(python3 -c "import json; print(json.load(open('$KEY_FILE'))['project_id'])")"
export GCP_PROJECT
echo "    Project: $GCP_PROJECT"

# ---------------------------------------------------------------------------
# Provision VM if it doesn't already exist
# ---------------------------------------------------------------------------
echo "==> Checking if VM '$VM_NAME' exists in $ZONE..."
if gcloud compute instances describe "$VM_NAME" \
     --zone "$ZONE" --project "$GCP_PROJECT" &>/dev/null; then
  echo "    VM already exists, skipping create."
else
  echo "==> Creating VM '$VM_NAME' in $ZONE..."
  gcloud compute instances create "$VM_NAME" \
    --zone "$ZONE" \
    --project "$GCP_PROJECT" \
    --machine-type e2-micro \
    --image-family debian-12 \
    --image-project debian-cloud \
    --tags http-server
fi

# Ensure the http-server firewall rule exists (allows TCP 80 from anywhere)
if ! gcloud compute firewall-rules describe default-allow-http \
       --project "$GCP_PROJECT" &>/dev/null; then
  echo "==> Creating firewall rule for TCP 80..."
  gcloud compute firewall-rules create default-allow-http \
    --project "$GCP_PROJECT" \
    --direction INGRESS \
    --action ALLOW \
    --rules tcp:80 \
    --target-tags http-server \
    --source-ranges 0.0.0.0/0
fi

# Derive SELECTOR_BASE_URL from the VM's external IP
EXTERNAL_IP="$(gcloud compute instances describe "$VM_NAME" \
  --zone "$ZONE" --project "$GCP_PROJECT" \
  --format 'get(networkInterfaces[0].accessConfigs[0].natIP)')"
export SELECTOR_BASE_URL="http://${EXTERNAL_IP}"
echo "    External IP: $EXTERNAL_IP"

# ---------------------------------------------------------------------------
# Delegate to bootstrap_selector.sh with env vars already exported
# ---------------------------------------------------------------------------
echo "==> Bootstrapping selector on $VM_NAME ($ZONE)..."
bash "$SCRIPT_DIR/bootstrap_selector.sh" "$VM_NAME" "$ZONE"

# ---------------------------------------------------------------------------
# Verification instructions
# ---------------------------------------------------------------------------
echo ""
echo "==> Iowa selector bootstrap complete."
echo ""
echo "  Selector: http://${EXTERNAL_IP}"
echo ""
echo "Verify:"
echo "  curl http://${EXTERNAL_IP}/health"
echo "  curl http://${EXTERNAL_IP}/api/status | python3 -m json.tool"
echo ""
echo "Point the dashboard at this selector:"
echo "  echo 'VITE_SELECTOR_BASE_URL=http://${EXTERNAL_IP}' > dash/.env.local"
echo ""
echo "Logs (SSH in):"
echo "  gcloud compute ssh $VM_NAME --zone $ZONE --project $GCP_PROJECT"
echo "  sudo journalctl -u dash-selector -f"
echo "  sudo tail -f /var/log/dash-selector/requests.log"
