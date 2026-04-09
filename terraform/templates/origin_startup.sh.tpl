#!/usr/bin/env bash
# Origin VM startup script — rendered by Terraform at apply time.
# Runs as root via GCP guest agent on first boot.
set -euo pipefail

apt-get update -y
apt-get install -y nginx

# Write origin identity so deploy.sh / debug scripts can read it
echo "origin_id=${origin_id}"   >  /etc/dash-origin-id
echo "region=${region_label}"   >> /etc/dash-origin-id

# Placeholder content so /health and NGINX work immediately after boot.
# Real DASH video files are deployed by deploy.sh (gcloud compute scp).
MANIFEST_DIR="/var/www/dash/video/dash_content/clip1"
mkdir -p "$MANIFEST_DIR"

cat > "$MANIFEST_DIR/manifest.mpd" <<'MPD'
<?xml version="1.0" encoding="UTF-8"?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT60S" minBufferTime="PT2S">
  <Period duration="PT60S">
    <AdaptationSet mimeType="video/mp4" segmentAlignment="true" codecs="avc1.42c01e">
      <Representation id="360p" bandwidth="800000" width="640" height="360" frameRate="30">
        <BaseURL>360p_dashinit.mp4</BaseURL>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
MPD

echo "placeholder-segment-data" > "$MANIFEST_DIR/360p_dashinit.mp4"

# NGINX config — matches nginx/nginx.conf with access/error logging added
cat > /etc/nginx/conf.d/dash.conf <<'NGINX'
server {
  listen 80;
  server_name _;

  access_log /var/log/nginx/dash_access.log;
  error_log  /var/log/nginx/dash_error.log;

  add_header Access-Control-Allow-Origin  "*" always;
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
    video/iso.segment    m4s;
    video/mp4            mp4;
  }
}
NGINX

chown -R www-data:www-data /var/www/dash
systemctl enable nginx
systemctl restart nginx
