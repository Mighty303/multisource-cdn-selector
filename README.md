# Multimedia Source Selection for a CDN

## Demo

<video src="https://github.com/user-attachments/assets/31fc4333-d45f-496f-9162-627d8d0f9da7" controls width="100%"></video>

This repository implements a simplified DASH CDN experiment on Google Cloud Platform using a custom Python selector instead of HAProxy as the primary decision layer.

## Test Flow

Use this section if the deployment already exists and you only need to verify the frontend and backend behavior.

### 1. Place the GCP key

Put the service account key at `scripts/key.json`:

```bash
mv key.json scripts/key.json
```

### 2. Load the environment

Source the repo's environment script:

```bash
source scripts/env.sh
```

This authenticates with GCP and exports `GCP_PROJECT`, `SELECTOR_BASE_URL`, `ORIGIN_VMS`, and `ORIGIN_ENDPOINTS`.

### 3. Verify the selector is up

```bash
curl http://cdn.martinwong.ca/health
curl http://cdn.martinwong.ca/api/status | python3 -m json.tool
```

If either command fails, re-bootstrap the selector VM:

```bash
ORIGIN_ENDPOINTS="$ORIGIN_ENDPOINTS" bash scripts/bootstrap_iowa_selector.sh scripts/key.json
```

### 4. Point the dashboard at the selector

```bash
echo 'VITE_SELECTOR_BASE_URL=http://cdn.martinwong.ca' > dash/.env.local
```

### 5. Start the frontend

```bash
cd dash && npm install && npm run dev
```

Open the Vite URL printed in the terminal, usually `http://localhost:5173`.


These verify manifest delivery, segment redirect behavior, and selector routing.

### 6. Backend: Run the full backend test matrix

If you also want to inspect backend behavior in more detail, run:

```bash
scripts/run_all_tests.sh
```

This writes CSV outputs to `new-results/`, including baseline runs and degraded-server runs for all three selector modes.

To generate the summary and open the two result charts:

```bash
python3 scripts/summarize_results.py new-results
open new-results/overall_avg_by_condition.svg
open new-results/delta_vs_baseline.svg
```

## Admin Workflow

The remaining sections are for provisioning, deployment, impairment testing, and log collection.

## Architecture

```text
Client -> Python Selector -> CDN Origin Servers
```

The selector:

- measures per-origin RTT with active health probes
- estimates throughput from a DASH segment sample
- tracks a lightweight load score from recent selections
- computes a selection score and chooses the best origin
- serves the MPD through the selector and redirects segment requests to the chosen origin

The default adaptive score is:

```text
score = latency_weight * latency_ms
      + load_weight * load_score
      - throughput_weight * throughput_mbps
```

Lower scores are preferred.

## Repo Layout

- `selector/`: Python selector runtime, metrics probes, and selection algorithm
- `nginx/`: NGINX origin configuration
- `dash-content/`: DASH packaging helper and generated media folder
- `scripts/`: GCP bootstrap, deploy, testing, and analysis scripts
- `tests/`: smoke tests for selector routing and segment delivery
- `haproxy/`: optional baseline HAProxy configs retained for comparison only

## Expected GCP Topology

Provision 4 Compute Engine VMs manually:

- 1 selector VM in Iowa
- 3 origin VMs in Oregon, Toronto, and Northern California

Recommended firewall posture:

- allow client -> selector on HTTP or HTTPS
- allow selector -> origins on HTTP
- restrict direct public media access to origins when possible

## Environment Setup

A pre-configured `scripts/env.sh` handles GCP authentication and sets all required variables. Source it once before running any scripts:

```bash
source scripts/env.sh
```

This activates the service account from `scripts/key.json` and exports `GCP_PROJECT`, `SELECTOR_BASE_URL`, `ORIGIN_VMS`, and `ORIGIN_ENDPOINTS` with the correct values for the deployed VMs.

## Deployment Workflow

1. Bootstrap each origin VM:

```bash
scripts/bootstrap_origin.sh <origin_vm_name> <origin_zone> oregon us-west1
scripts/bootstrap_origin.sh <origin_vm_name> <origin_zone> toronto northamerica-northeast2
scripts/bootstrap_origin.sh <origin_vm_name> <origin_zone> ncalifornia us-west2
```

2. Bootstrap the selector VM:

```bash
bash scripts/bootstrap_selector.sh <selector_vm_name> <selector_zone>
```

3. Deploy selector code and DASH content:

```bash
scripts/deploy.sh
```

Before deploying, generate real DASH assets under `dash-content/video/`. `deploy.sh` now fails fast if that folder only contains placeholders or if the configured probe segment path does not exist.

## Selector Modes

The selector supports three modes:

- `adaptive`: custom score-based source selection
- `random`: random healthy origin selection baseline
- `round_robin`: deterministic healthy-origin rotation baseline

Change the mode with:

```bash
scripts/switch_algorithm.sh adaptive
scripts/switch_algorithm.sh random
scripts/switch_algorithm.sh round_robin
```

The selector exposes:

- `/health`: service health check
- `/api/status`: current selector mode, origins, and cached metrics
- `/admin/mode?value=<mode>`: updates the active selection mode

## Testing and Analysis

- Segment smoke test:

```bash
tests/test_segments.sh
```

- Selector routing smoke test:

```bash
tests/test_routing.sh
```

- Run the full test matrix (baseline + each server degraded, all 3 modes) into `new-results/`:

```bash
scripts/run_all_tests.sh
```

Output: one CSV per mode per condition (e.g. `new-results/adaptive_baseline.csv`, `new-results/random_toronto_degraded.csv`). No JSONL files are written to this folder.

- Run a single mode/condition manually:

```bash
scripts/run_tests.sh results/load_test_results.csv adaptive
```

- Apply network impairment to an origin:

```bash
scripts/simulate_network.sh toronto 200 5
```

- Remove network impairment:

```bash
scripts/reset_network.sh toronto      # single server
scripts/reset_network.sh all          # all origin servers
```

- Collect and parse selector logs:

```bash
scripts/collect_logs.sh results/selector.log
python3 scripts/parse_logs.py results/selector.log
```

## Logging and Metrics

The selector writes JSONL logs for each MPD decision and redirect, including:

- selected server
- selector mode
- per-origin score snapshot
- per-origin RTT, throughput, and load values
- decision latency
- request target and response status

These logs are intended for comparison against baseline modes such as `random` and `round_robin`.

## Required CLI Tools

- `gcloud` (authentication is handled automatically via `key.json` when you `source env.sh`)
- `curl`
- `python3`
- `ffmpeg` for local DASH encoding only

## Windows Notes

- Install the Google Cloud CLI from the official docs: https://cloud.google.com/sdk/docs/install-sdk
- After installation, open a new terminal and run `gcloud init` to authenticate and select your GCP project.
- `gcloud` commands can be run from PowerShell once the CLI is on `PATH`.
- Repo scripts under `scripts/*.sh` use Bash syntax, so run them from Git Bash or WSL after loading `scripts/env.example`.
