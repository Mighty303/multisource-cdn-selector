#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <server_id|all>" >&2
  exit 1
fi

TARGET="$1"

require_cmd gcloud
require_gcp_project
require_env ORIGIN_VMS

clear_one() {
  local server_id="$1"
  local vm zone

  if ! read -r vm zone < <(find_origin_vm "$server_id"); then
    echo "server_id '$server_id' not found in ORIGIN_VMS" >&2
    exit 1
  fi

  local remote_cmd
  remote_cmd=$(cat <<'EOF'
IFACE=$(ip route show default | awk '{print $5; exit}')
if [[ -z "$IFACE" ]]; then
  echo "Could not detect default network interface" >&2
  exit 1
fi
sudo tc qdisc del dev "$IFACE" root 2>/dev/null || true
echo "Cleared netem on interface $IFACE"
EOF
)

  gssh "$vm" "$zone" "$remote_cmd"
  echo "Cleared network impairment on $server_id ($vm)"
}

if [[ "$TARGET" == "all" ]]; then
  for entry in ${ORIGIN_VMS//,/ }; do
    clear_one "${entry%%:*}"
  done
else
  clear_one "$TARGET"
fi
