#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <selector_vm_name> <zone>" >&2
  exit 1
fi

VM_NAME="$1"
ZONE="$2"
SELECTOR_SERVICE_PORT="${SELECTOR_SERVICE_PORT:-80}"

require_cmd gcloud
require_gcp_project
require_env SELECTOR_BASE_URL
require_env ORIGIN_ENDPOINTS

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

write_selector_config "$TMP_DIR/config.json"

cat > "$TMP_DIR/bootstrap_selector.remote.sh" <<REMOTE
#!/usr/bin/env bash
set -euo pipefail

SELECTOR_SERVICE_PORT="${SELECTOR_SERVICE_PORT}"

sudo apt-get update -y
sudo apt-get install -y python3

sudo mkdir -p /opt/dash-selector /etc/dash-selector /var/log/dash-selector
sudo rm -rf /opt/dash-selector/selector
sudo cp -r ~/dash-selector/selector /opt/dash-selector/selector
sudo cp ~/dash-selector/config.json /etc/dash-selector/config.json

sudo tee /etc/systemd/system/dash-selector.service > /dev/null <<'UNIT'
[Unit]
Description=Custom DASH selector service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/dash-selector
ExecStart=/usr/bin/python3 -m selector.server --config /etc/dash-selector/config.json --bind 0.0.0.0 --port ${SELECTOR_SERVICE_PORT} --log-file /var/log/dash-selector/requests.log
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

chmod +x "$TMP_DIR/bootstrap_selector.remote.sh"

gssh "$VM_NAME" "$ZONE" "rm -rf ~/dash-selector && mkdir -p ~/dash-selector"
gscp_to_recursive "$REPO_ROOT/selector" "$VM_NAME" "$ZONE" "~/dash-selector"
gscp_to "$TMP_DIR/config.json" "$VM_NAME" "$ZONE" "~/dash-selector/config.json"
gscp_to "$TMP_DIR/bootstrap_selector.remote.sh" "$VM_NAME" "$ZONE" "~/bootstrap_selector.sh"
gssh "$VM_NAME" "$ZONE" "chmod +x ~/bootstrap_selector.sh && ~/bootstrap_selector.sh"

echo "Selector bootstrap completed on $VM_NAME ($ZONE)."
