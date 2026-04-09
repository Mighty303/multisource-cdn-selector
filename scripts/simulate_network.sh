#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <server_id> <latency_ms> <loss_percent>" >&2
  exit 1
fi

SERVER_ID="$1"
LATENCY_MS="$2"
LOSS_PERCENT="$3"

require_cmd gcloud
require_gcp_project

if ! read -r TARGET_VM TARGET_ZONE < <(find_origin_vm "$SERVER_ID"); then
  echo "server_id '$SERVER_ID' not found in ORIGIN_VMS" >&2
  exit 1
fi

REMOTE_CMD=$(cat <<EOF
IFACE=\$(ip route show default | awk '{print \$5; exit}')
if [[ -z "\$IFACE" ]]; then
  echo "Could not detect default network interface" >&2
  exit 1
fi
sudo tc qdisc replace dev "\$IFACE" root netem delay ${LATENCY_MS}ms loss ${LOSS_PERCENT}%
echo "Applied netem on interface \$IFACE"
EOF
)

gssh "$TARGET_VM" "$TARGET_ZONE" "$REMOTE_CMD"

echo "Applied tc rule on $SERVER_ID ($TARGET_VM): ${LATENCY_MS}ms delay, ${LOSS_PERCENT}% loss"
