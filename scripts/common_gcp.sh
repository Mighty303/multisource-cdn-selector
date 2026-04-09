#!/usr/bin/env bash
set -euo pipefail

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Required command not found: $cmd" >&2
    if [[ "$cmd" == "gcloud" ]]; then
      cat >&2 <<'EOF'
Install the Google Cloud CLI first:
  https://cloud.google.com/sdk/docs/install-sdk

Windows notes:
  - Restart your terminal after installation so gcloud is added to PATH.
  - Run this repo's .sh scripts from Bash (Git Bash or WSL), not PowerShell.
  - After install, run: gcloud init
EOF
    fi
    exit 1
  fi
}

require_gcp_project() {
  if [[ -z "${GCP_PROJECT:-}" ]]; then
    echo "GCP_PROJECT env var is required" >&2
    exit 1
  fi
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "${name} env var is required" >&2
    exit 1
  fi
}

# ORIGIN_VMS format:
# oregon:<vm-name>:<zone>,toronto:<vm-name>:<zone>,ncalifornia:<vm-name>:<zone>
find_origin_vm() {
  local server_id="$1"
  if [[ -z "${ORIGIN_VMS:-}" ]]; then
    echo "ORIGIN_VMS env var is required" >&2
    exit 1
  fi

  local entry id rest vm zone
  for entry in ${ORIGIN_VMS//,/ }; do
    id="${entry%%:*}"
    rest="${entry#*:}"
    vm="${rest%%:*}"
    zone="${rest##*:}"
    if [[ "$id" == "$server_id" ]]; then
      echo "$vm $zone"
      return 0
    fi
  done

  return 1
}

# ORIGIN_ENDPOINTS format:
# oregon:http://10.0.0.10,toronto:http://10.0.1.10,ncalifornia:http://10.0.2.10
find_origin_endpoint() {
  local server_id="$1"
  if [[ -z "${ORIGIN_ENDPOINTS:-}" ]]; then
    echo "ORIGIN_ENDPOINTS env var is required" >&2
    exit 1
  fi

  local entry id endpoint
  for entry in ${ORIGIN_ENDPOINTS//,/ }; do
    id="${entry%%:*}"
    endpoint="${entry#*:}"
    if [[ "$id" == "$server_id" ]]; then
      echo "$endpoint"
      return 0
    fi
  done

  return 1
}

write_selector_config() {
  local dest="$1"

  require_env SELECTOR_BASE_URL
  require_env ORIGIN_ENDPOINTS

  local selector_mode="${SELECTOR_MODE:-adaptive}"
  local weight_latency="${SELECTOR_WEIGHT_LATENCY:-0.65}"
  local weight_load="${SELECTOR_WEIGHT_LOAD:-0.25}"
  local weight_throughput="${SELECTOR_WEIGHT_THROUGHPUT:-0.10}"
  local probe_health_path="${SELECTOR_HEALTH_PATH:-/health}"
  local probe_throughput_path="${SELECTOR_SEGMENT_PATH:-${SELECTOR_THROUGHPUT_PATH:-/video/dash_content/clip1/360p_dashinit.mp4}}"
  local probe_manifest_path="${SELECTOR_MANIFEST_PATH:-/video/dash_content/clip1/manifest.mpd}"
  local probe_timeout="${SELECTOR_PROBE_TIMEOUT_SECONDS:-2.0}"
  local probe_ttl="${SELECTOR_PROBE_TTL_SECONDS:-5.0}"
  local sample_bytes="${SELECTOR_THROUGHPUT_SAMPLE_BYTES:-262144}"
  local entry id base_url
  local first=1

  {
    echo '{'
    echo "  \"public_base_url\": \"${SELECTOR_BASE_URL}\","
    echo "  \"mode\": \"${selector_mode}\","
    echo '  "weights": {'
    echo "    \"latency\": ${weight_latency},"
    echo "    \"load\": ${weight_load},"
    echo "    \"throughput\": ${weight_throughput}"
    echo '  },'
    echo '  "probe": {'
    echo "    \"health_path\": \"${probe_health_path}\","
    echo "    \"throughput_path\": \"${probe_throughput_path}\","
    echo "    \"manifest_path\": \"${probe_manifest_path}\","
    echo "    \"timeout_seconds\": ${probe_timeout},"
    echo "    \"ttl_seconds\": ${probe_ttl},"
    echo "    \"sample_bytes\": ${sample_bytes}"
    echo '  },'
    echo '  "origins": ['
    for entry in ${ORIGIN_ENDPOINTS//,/ }; do
      id="${entry%%:*}"
      base_url="${entry#*:}"
      if [[ $first -eq 0 ]]; then
        echo ','
      fi
      printf '    {"id": "%s", "base_url": "%s"}' "$id" "$base_url"
      first=0
    done
    echo
    echo '  ]'
    echo '}'
  } > "$dest"
}

gssh() {
  local vm="$1"
  local zone="$2"
  local cmd="$3"
  gcloud compute ssh "$vm" \
    --zone "$zone" \
    --project "$GCP_PROJECT" \
    --command "$cmd"
}

gscp_to() {
  local src="$1"
  local vm="$2"
  local zone="$3"
  local dest="$4"
  gcloud compute scp "$src" "$vm:$dest" \
    --zone "$zone" \
    --project "$GCP_PROJECT"
}

gscp_to_recursive() {
  local src="$1"
  local vm="$2"
  local zone="$3"
  local dest="$4"
  gcloud compute scp --recurse "$src" "$vm:$dest" \
    --zone "$zone" \
    --project "$GCP_PROJECT"
}
