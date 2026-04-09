#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common_gcp.sh
source "$SCRIPT_DIR/common_gcp.sh"

if [[ $# -lt 4 ]]; then
  echo "Usage: $0 <vm_name> <zone> <origin_id> <region_label>" >&2
  exit 1
fi

VM_NAME="$1"
ZONE="$2"
ORIGIN_ID="$3"
REGION_LABEL="$4"
MANIFEST_PATH="${SELECTOR_MANIFEST_PATH:-/video/dash_content/clip1/manifest.mpd}"
PROBE_SEGMENT_PATH="${SELECTOR_SEGMENT_PATH:-${SELECTOR_THROUGHPUT_PATH:-/video/dash_content/clip1/360p_dashinit.mp4}}"

require_cmd gcloud
require_gcp_project

TMP_SCRIPT="$(mktemp)"
cat > "$TMP_SCRIPT" <<'REMOTE'
#!/usr/bin/env bash
set -euo pipefail

ORIGIN_ID="$1"
REGION_LABEL="$2"
MANIFEST_PATH="$3"
PROBE_SEGMENT_PATH="$4"

sudo apt-get update -y
sudo apt-get install -y nginx

MANIFEST_FILE="/var/www/dash${MANIFEST_PATH}"
SEGMENT_FILE="/var/www/dash${PROBE_SEGMENT_PATH}"
SEGMENT_BASENAME="$(basename "$PROBE_SEGMENT_PATH")"

sudo mkdir -p "$(dirname "$MANIFEST_FILE")"
sudo mkdir -p "$(dirname "$SEGMENT_FILE")"
sudo tee "$MANIFEST_FILE" > /dev/null <<MPD
<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT60S" minBufferTime="PT2S">
  <Period duration="PT60S">
    <AdaptationSet mimeType="video/mp4" segmentAlignment="true" codecs="avc1.42c01e">
      <Representation id="360p" bandwidth="800000" width="640" height="360" frameRate="30">
        <BaseURL>${SEGMENT_BASENAME}</BaseURL>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
MPD

echo "placeholder-segment-data" | sudo tee "$SEGMENT_FILE" >/dev/null

sudo tee /etc/nginx/conf.d/dash.conf > /dev/null <<'NGINX'
server {
  listen 80;
  server_name _;

  access_log /var/log/nginx/dash_access.log;
  error_log /var/log/nginx/dash_error.log;

  add_header Access-Control-Allow-Origin "*" always;
  add_header Access-Control-Allow-Methods "GET,HEAD,OPTIONS" always;
  add_header Access-Control-Allow-Headers "*" always;

  location = /health {
    add_header Content-Type text/plain;
    return 200 'ok';
  }

  location / {
    root /var/www/dash;
    try_files $uri $uri/ =404;
  }

  types {
    application/dash+xml mpd;
    video/iso.segment m4s;
    video/mp4 mp4;
  }
}
NGINX

echo "origin_id=${ORIGIN_ID}" | sudo tee /etc/dash-origin-id >/dev/null
echo "region=${REGION_LABEL}" | sudo tee -a /etc/dash-origin-id >/dev/null

sudo chown -R www-data:www-data /var/www/dash
sudo systemctl enable nginx
sudo systemctl restart nginx
REMOTE

chmod +x "$TMP_SCRIPT"
gscp_to "$TMP_SCRIPT" "$VM_NAME" "$ZONE" "~/bootstrap_origin.sh"
gssh "$VM_NAME" "$ZONE" "chmod +x ~/bootstrap_origin.sh && ~/bootstrap_origin.sh '$ORIGIN_ID' '$REGION_LABEL' '$MANIFEST_PATH' '$PROBE_SEGMENT_PATH'"

rm -f "$TMP_SCRIPT"
echo "Origin bootstrap completed for $ORIGIN_ID on $VM_NAME ($ZONE)."
