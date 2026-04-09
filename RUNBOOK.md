# SecureStream Runbook

End-to-end commands to deploy the Iowa selector VM, wire up the dashboard, and run all tests.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| `terraform` | 1.5+ | https://developer.hashicorp.com/terraform/install |
| `gcloud` | any | https://cloud.google.com/sdk/docs/install-sdk |
| `python3` | 3.8+ | `brew install python` / system package |
| `node` | 18+ | https://nodejs.org |
| `npm` | 9+ | bundled with Node |
| `curl` | any | system |

A GCP **service account key file** (`key.json`) in the repo root with at minimum:
- `compute.instances.create` / `get` / `describe`
- `compute.firewalls.create` / `get`
- `compute.sshMetadataKeys.set` (for `gcloud compute ssh/scp` used by `deploy.sh`)

---

## Step 1 — Install frontend dependencies

```bash
cd dash
npm install
cd ..
```

---

## Step 2 — Provision all VMs with Terraform

```bash
cd terraform
terraform init
terraform apply
cd ..
```

This creates **4 VMs + 1 firewall rule** in ~3 minutes:
- `dash-selector-iowa` (us-central1-a) — Python WSGI selector
- `dash-origin-oregon` (us-west1-b) — NGINX origin
- `dash-origin-toronto` (northamerica-northeast2-a) — NGINX origin
- `dash-origin-ncalifornia` (us-west2-b) — NGINX origin

Origin IPs are automatically injected into the selector's `config.json` — no manual IP copying required.

---

## Step 3 — Deploy selector code and DASH content

```bash
export GCP_PROJECT=cmpt471-cdn-project
export SELECTOR_VM=dash-selector-iowa
export SELECTOR_ZONE=us-central1-a
export SELECTOR_BASE_URL=http://$(cd terraform && terraform output -raw selector_ip)
export ORIGIN_VMS=oregon:dash-origin-oregon:us-west1-b,toronto:dash-origin-toronto:northamerica-northeast2-a,ncalifornia:dash-origin-ncalifornia:us-west2-b
export ORIGIN_ENDPOINTS=$(cd terraform && terraform output -raw origin_endpoints)

bash scripts/deploy.sh
```

`deploy.sh` pushes the `selector/` Python package and `dash-content/video/` DASH segments to all VMs via `gcloud compute scp`.

---

## Step 4 — Verify the selector is running

```bash
export SELECTOR_BASE_URL=http://$(cd terraform && terraform output -raw selector_ip)

# Liveness check
curl $SELECTOR_BASE_URL/health
# Expected: ok

# Full status (mode, origins, live metrics)
curl $SELECTOR_BASE_URL/api/status | python3 -m json.tool

# Stream manifest (selector proxies and rewrites BaseURL)
curl $SELECTOR_BASE_URL/video/dash_content/clip1/manifest.mpd

# Media file (selector issues a 302 redirect to the chosen origin)
curl -v $SELECTOR_BASE_URL/video/dash_content/clip1/360p_dashinit.mp4 2>&1 | grep -i location
```

Or use the pre-built verify commands output by Terraform:

```bash
cd terraform && terraform output verify_commands
```

---

## Step 5 — Wire the dashboard to the selector

```bash
echo "VITE_SELECTOR_BASE_URL=http://$(cd terraform && terraform output -raw selector_ip)" > dash/.env.local
```

---

## Step 6 — Run the frontend dev server

```bash
cd dash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). On the **Network** page you should see:
- A purple diamond labelled **SELECTOR / IOWA** on the map, pulsing to indicate a live connection
- The Incident Log shows a pulsing **LIVE** badge and live routing decisions every 5 s

---

## Step 7 — Run frontend unit tests

```bash
cd dash
npm test
```

Expected output:

```
✓ src/test/example.test.ts        (1 test)
✓ src/test/selectorApi.test.ts    (6 tests)
✓ src/test/mockData.test.ts       (11 tests)

Test Files  3 passed (3)
     Tests  18 passed (18)
```

---

## Step 8 — Run selector integration tests

Requires `SELECTOR_BASE_URL` and `ORIGIN_ENDPOINTS` to be set (from Step 3).

```bash
# Connectivity + manifest + segment redirect
bash tests/test_segments.sh

# Round-robin routing + adaptive mode status check
bash tests/test_routing.sh
```

---

## Operational commands

### Tear down all VMs

```bash
cd terraform && terraform destroy
```

### Re-deploy selector code after a code change

```bash
bash scripts/deploy.sh   # env vars already set from Step 3
```

### Switch routing algorithm at runtime

```bash
export SELECTOR_BASE_URL=http://$(cd terraform && terraform output -raw selector_ip)

bash scripts/switch_algorithm.sh adaptive      # latency-weighted (default)
bash scripts/switch_algorithm.sh round_robin   # strict round-robin
bash scripts/switch_algorithm.sh random        # random selection
```

### Tail selector logs (SSH into VM)

```bash
gcloud compute ssh dash-selector-iowa \
  --zone us-central1-a \
  --project cmpt471-cdn-project

# On the VM:
sudo journalctl -u dash-selector -f
sudo tail -f /var/log/dash-selector/requests.log
```

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `curl /health` times out | Firewall rule `default-allow-http` exists in project; VM has tag `http-server` |
| `/api/status` shows all origins unhealthy | `ORIGIN_ENDPOINTS` IPs reachable from the Iowa VM; origin `/health` returns `ok` |
| Dashboard shows no live data | `dash/.env.local` contains correct `VITE_SELECTOR_BASE_URL`; dev server restarted after editing `.env.local` |
| `test_routing.sh` fails round-robin step | `switch_algorithm.sh` requires `SELECTOR_BASE_URL`; confirm it is exported |
| `gcloud compute ssh` hangs | Run `gcloud compute config-ssh --project <project>` once to refresh OS Login keys |
