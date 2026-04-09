#!/usr/bin/env bash
# Source this file before running any scripts:
#   source env.sh

gcloud auth activate-service-account --key-file="$(dirname "${BASH_SOURCE[0]}")/key.json" 2>/dev/null

export GCP_PROJECT="cmpt471-cdn-project"
export SELECTOR_BASE_URL="http://cdn.martinwong.ca"
export ORIGIN_VMS="oregon:dash-origin-oregon:us-west1-b,toronto:dash-origin-toronto:northamerica-northeast2-a,ncalifornia:dash-origin-ncalifornia:us-west2-b"
export ORIGIN_ENDPOINTS="oregon:http://136.117.216.224,toronto:http://34.130.216.13,ncalifornia:http://35.236.73.111"

echo "Environment ready."
