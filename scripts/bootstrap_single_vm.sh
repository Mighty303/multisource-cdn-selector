#!/usr/bin/env bash
# bootstrap_single_vm.sh — Spin up one GCP VM with NGINX origin (port 8080)
# and the Python selector (port 80) to smoke-test source selection end-to-end.
#
# Usage:
#   bash scripts/bootstrap_single_vm.sh <key.json> [vm-name] [zone]
#
# Examples:
#   bash scripts/bootstrap_single_vm.sh key.json
#   bash scripts/bootstrap_single_vm.sh key.json dash-single us-west1-b
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <key.json> [vm-name] [zone]" >&2
  exit 1
fi

KEY_FILE="$(realpath "$1")"
VM_NAME="${2:-dash-single}"
ZONE="${3:-us-west1-b}"
SELECTOR_PORT=80
ORIGIN_PORT=8080
MANIFEST_PATH="${SELECTOR_MANIFEST_PATH:-/video/dash_content/clip1/manifest.mpd}"
PROBE_SEGMENT_PATH="${SELECTOR_SEGMENT_PATH:-${SELECTOR_THROUGHPUT_PATH:-/video/dash_content/clip1/360p_dashinit.mp4}}"

require_cmd gcloud
require_cmd python3

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
# Step A: Provision VM if it doesn't already exist
# ---------------------------------------------------------------------------
echo "==> Checking if VM '$VM_NAME' exists..."
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

# Derive SELECTOR_BASE_URL from the VM's external IP (no env var needed)
EXTERNAL_IP="$(gcloud compute instances describe "$VM_NAME" \
  --zone "$ZONE" --project "$GCP_PROJECT" \
  --format 'get(networkInterfaces[0].accessConfigs[0].natIP)')"
export SELECTOR_BASE_URL="http://${EXTERNAL_IP}"
echo "    External IP: $EXTERNAL_IP"

# ---------------------------------------------------------------------------
# Step B+D: Build and transfer the combined remote bootstrap script
# ---------------------------------------------------------------------------
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Generate selector config pointing to the local origin on port 8080
export ORIGIN_ENDPOINTS="local:http://localhost:${ORIGIN_PORT}"
write_selector_config "$TMP_DIR/config.json"

cat > "$TMP_DIR/bootstrap_single_vm.remote.sh" <<REMOTE
#!/usr/bin/env bash
set -euo pipefail

ORIGIN_PORT=${ORIGIN_PORT}
SELECTOR_PORT=${SELECTOR_PORT}

sudo apt-get update -y
sudo apt-get install -y nginx python3

# --- Origin: NGINX on port \$ORIGIN_PORT ---
MANIFEST_FILE="/var/www/dash${MANIFEST_PATH}"
SEGMENT_FILE="/var/www/dash${PROBE_SEGMENT_PATH}"
SEGMENT_BASENAME="$(basename "${PROBE_SEGMENT_PATH}")"

sudo mkdir -p "$(dirname "\$MANIFEST_FILE")"
sudo mkdir -p "$(dirname "\$SEGMENT_FILE")"

sudo tee "\$MANIFEST_FILE" > /dev/null <<MPD
<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT60S" minBufferTime="PT2S">
  <Period duration="PT60S">
    <AdaptationSet mimeType="video/mp4" segmentAlignment="true" codecs="avc1.42c01e">
      <Representation id="360p" bandwidth="800000" width="640" height="360" frameRate="30">
        <BaseURL>\${SEGMENT_BASENAME}</BaseURL>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
MPD

echo "placeholder-segment-data" | sudo tee "\$SEGMENT_FILE" >/dev/null

sudo tee /etc/nginx/conf.d/dash-origin.conf > /dev/null <<NGINX
server {
  listen \${ORIGIN_PORT};
  server_name _;

  access_log /var/log/nginx/dash_access.log;
  error_log  /var/log/nginx/dash_error.log;

  add_header Access-Control-Allow-Origin "*" always;
  add_header Access-Control-Allow-Methods "GET,HEAD,OPTIONS" always;
  add_header Access-Control-Allow-Headers "*" always;

  location = /health {
    add_header Content-Type text/plain;
    return 200 'ok';
  }

  location / {
    root /var/www/dash;
    try_files \\\$uri \\\$uri/ =404;
  }

  types {
    application/dash+xml mpd;
    video/iso.segment   m4s;
    video/mp4           mp4;
  }
}
NGINX

# Disable default NGINX site so it doesn't grab port 80
sudo rm -f /etc/nginx/sites-enabled/default

sudo chown -R www-data:www-data /var/www/dash
sudo systemctl enable nginx
sudo systemctl restart nginx

# --- Selector: Python selector on port \$SELECTOR_PORT ---
sudo mkdir -p /opt/dash-selector /etc/dash-selector /var/log/dash-selector
sudo rm -rf /opt/dash-selector/selector
sudo cp -r ~/dash-selector/selector /opt/dash-selector/selector
sudo cp ~/dash-selector/config.json /etc/dash-selector/config.json

sudo tee /etc/systemd/system/dash-selector.service > /dev/null <<UNIT
[Unit]
Description=DASH selector service (single-VM smoke test)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/dash-selector
ExecStart=/usr/bin/python3 -m selector.server \
  --config /etc/dash-selector/config.json \
  --bind 0.0.0.0 \
  --port ${SELECTOR_PORT} \
  --log-file /var/log/dash-selector/requests.log
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable dash-selector
sudo systemctl restart dash-selector
sudo systemctl --no-pager --full status dash-selector
REMOTE

chmod +x "$TMP_DIR/bootstrap_single_vm.remote.sh"

# ---------------------------------------------------------------------------
# Step C: Copy selector code and generated config to the VM
# ---------------------------------------------------------------------------
echo "==> Uploading selector code..."
gssh "$VM_NAME" "$ZONE" "rm -rf ~/dash-selector && mkdir -p ~/dash-selector"
gscp_to_recursive "$REPO_ROOT/selector" "$VM_NAME" "$ZONE" "~/dash-selector"
gscp_to "$TMP_DIR/config.json" "$VM_NAME" "$ZONE" "~/dash-selector/config.json"
gscp_to "$TMP_DIR/bootstrap_single_vm.remote.sh" "$VM_NAME" "$ZONE" "~/bootstrap_single_vm.remote.sh"

# ---------------------------------------------------------------------------
# Run remote bootstrap
# ---------------------------------------------------------------------------
echo "==> Running remote bootstrap on $VM_NAME..."
gssh "$VM_NAME" "$ZONE" "chmod +x ~/bootstrap_single_vm.remote.sh && ~/bootstrap_single_vm.remote.sh"

# ---------------------------------------------------------------------------
# Print verification instructions
# ---------------------------------------------------------------------------
echo ""
echo "==> Bootstrap complete."
echo ""
echo "  Selector: http://${EXTERNAL_IP}"
echo ""
echo "Verify:"
echo "  curl http://${EXTERNAL_IP}/health"
echo "  curl http://${EXTERNAL_IP}/api/status | python3 -m json.tool"
echo "  SELECTOR_BASE_URL=http://${EXTERNAL_IP} SELECTOR_MANIFEST_PATH=${MANIFEST_PATH} SELECTOR_SEGMENT_PATH=${PROBE_SEGMENT_PATH} bash tests/test_segments.sh"
echo "  SELECTOR_BASE_URL=http://${EXTERNAL_IP} ORIGIN_ENDPOINTS=local:http://localhost:8080 SELECTOR_SEGMENT_PATH=${PROBE_SEGMENT_PATH} bash tests/test_routing.sh"
echo ""
echo "Logs (SSH in):"
echo "  sudo journalctl -u dash-selector -f"
echo "  sudo tail -f /var/log/dash-selector/requests.log"
