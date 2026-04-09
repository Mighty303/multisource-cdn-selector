#!/usr/bin/env bash
# Selector VM startup script — rendered by Terraform at apply time.
# Origin IPs are baked into config.json at terraform apply time.
# Runs as root via GCP guest agent on first boot.
set -euo pipefail

apt-get update -y
apt-get install -y python3

mkdir -p /opt/dash-selector /etc/dash-selector /var/log/dash-selector

# Write config.json with real origin IPs injected by Terraform.
# Note: public_base_url is left empty — the selector's own external IP is unknown
# at provision time. deploy.sh sets it correctly after terraform apply.
cat > /etc/dash-selector/config.json <<'CONFIG'
{
  "public_base_url": "",
  "mode": "${selector_mode}",
  "weights": {
    "latency":    ${weight_latency},
    "load":       ${weight_load},
    "throughput": ${weight_throughput}
  },
  "probe": {
    "health_path":     "/health",
    "throughput_path": "/video/dash_content/clip1/360p_dashinit.mp4",
    "manifest_path":   "/video/dash_content/clip1/manifest.mpd",
    "timeout_seconds": ${probe_timeout_seconds},
    "ttl_seconds":     ${probe_ttl_seconds},
    "sample_bytes":    ${probe_sample_bytes}
  },
  "origins": ${origins_json}
}
CONFIG

# Register systemd service.
# The selector Python package is NOT deployed here — deploy.sh copies it via gcloud scp.
# The service will fail on start until deploy.sh has run; this is intentional.
# Infrastructure is ready; code deploy is a separate step.
cat > /etc/systemd/system/dash-selector.service <<'UNIT'
[Unit]
Description=Custom DASH selector service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/dash-selector
ExecStart=/usr/bin/python3 -m selector.server \
  --config /etc/dash-selector/config.json \
  --bind 0.0.0.0 \
  --port ${selector_port} \
  --log-file /var/log/dash-selector/requests.log
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable dash-selector
# Start is attempted; it will fail gracefully until deploy.sh installs the Python package.
systemctl start dash-selector || true
