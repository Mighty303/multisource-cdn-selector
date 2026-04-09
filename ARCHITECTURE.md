# Architecture

## Overview

This project implements a DASH-based multimedia source-selection CDN on Google Cloud using a custom Python selector.

Runtime path:

```text
Browser / Dashboard
        |
        v
Python Selector VM
        |
        +----> Oregon Origin VM
        +----> Toronto Origin VM
        +----> N. California Origin VM
```

The selector is a separate network service. It is not part of the browser player.

## Main Components

### 1. Selector

Path:

- [selector/server.py](/Users/anguscheng/Desktop/multimedia-src-selection/selector/server.py)
- [selector/SelectorHandler.py](/Users/anguscheng/Desktop/multimedia-src-selection/selector/SelectorHandler.py)
- [selector/SelectorState.py](/Users/anguscheng/Desktop/multimedia-src-selection/selector/SelectorState.py)
- [selector/algorithm.py](/Users/anguscheng/Desktop/multimedia-src-selection/selector/algorithm.py)
- [selector/MetricsCollector.py](/Users/anguscheng/Desktop/multimedia-src-selection/selector/MetricsCollector.py)
- [selector/LoadTracker.py](/Users/anguscheng/Desktop/multimedia-src-selection/selector/LoadTracker.py)

Responsibilities:

- expose `/health`
- expose `/api/status`
- expose `/api/logs`
- expose admin endpoints for mode switching and failure injection
- probe origin health, latency, throughput, and load
- choose an origin using `adaptive`, `random`, or `round_robin`
- fetch and rewrite DASH manifests
- redirect media requests to the chosen origin
- log routing events as JSONL

### 2. Origin Servers

Path:

- [nginx/nginx.conf](/Users/anguscheng/Desktop/multimedia-src-selection/nginx/nginx.conf)
- [scripts/bootstrap_origin.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/bootstrap_origin.sh)

Responsibilities:

- serve identical DASH content from `/var/www/dash/video`
- expose `/health`
- serve `.mpd`, `.mp4`, and `.m4s`
- provide CORS headers for browser playback

### 3. DASH Content

Path:

- [dash-content/encode.sh](/Users/anguscheng/Desktop/multimedia-src-selection/dash-content/encode.sh)
- `dash-content/video/dash_content/clip1..clip6`

Responsibilities:

- store generated DASH manifests and media segments
- provide identical content to each origin VM

### 4. Frontend Dashboard

Path:

- [dash/src/lib/mockData.ts](/Users/anguscheng/Desktop/multimedia-src-selection/dash/src/lib/mockData.ts)
- [dash/src/lib/selectorApi.ts](/Users/anguscheng/Desktop/multimedia-src-selection/dash/src/lib/selectorApi.ts)
- [dash/src/hooks/useLiveData.ts](/Users/anguscheng/Desktop/multimedia-src-selection/dash/src/hooks/useLiveData.ts)
- [dash/src/components/soc/IncidentLog.tsx](/Users/anguscheng/Desktop/multimedia-src-selection/dash/src/components/soc/IncidentLog.tsx)
- [dash/src/pages/Analytics.tsx](/Users/anguscheng/Desktop/multimedia-src-selection/dash/src/pages/Analytics.tsx)

Responsibilities:

- request playback through the selector MPD URL
- poll `/api/status` for live origin metrics
- poll `/api/logs` for real selector events
- show incident/debug entries from actual selector logs

### 5. Operations and Test Scripts

Path:

- [scripts/deploy.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/deploy.sh)
- [scripts/bootstrap_selector.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/bootstrap_selector.sh)
- [scripts/switch_algorithm.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/switch_algorithm.sh)
- [scripts/simulate_network.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/simulate_network.sh)
- [scripts/collect_logs.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/collect_logs.sh)
- [scripts/run_tests.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/run_tests.sh)
- [tests/test_segments.sh](/Users/anguscheng/Desktop/multimedia-src-selection/tests/test_segments.sh)
- [tests/test_routing.sh](/Users/anguscheng/Desktop/multimedia-src-selection/tests/test_routing.sh)

Responsibilities:

- provision service config on VMs
- deploy selector code and DASH content
- switch runtime selector mode
- inject network impairment with `tc netem`
- collect selector logs
- run smoke and load tests

## Runtime Topology

Expected 4-VM layout:

- `dash-selector-iowa`: selector VM
- `dash-origin-oregon`: origin VM
- `dash-origin-toronto`: origin VM
- `dash-origin-ncalifornia`: origin VM

Public selector address:

- `http://cdn.martinwong.ca`

Public origin addresses are still used internally by the selector config in the current deployment.

## Full Request Flow

### A. User starts playback

1. The frontend loads a camera MPD URL such as:

```text
http://cdn.martinwong.ca/video/dash_content/clip1/manifest.mpd
```

2. The browser sends the MPD request to the selector.

### B. Selector handles the manifest

3. The selector probes or reuses cached metrics for all origins.
4. The selector chooses one origin using the active mode.
5. The selector fetches the manifest from that chosen origin.
6. The selector rewrites manifest `BaseURL` values so subsequent media requests still return through the selector.
7. The selector sends the rewritten MPD back to the browser.
8. The selector logs a `decision_manifest` event.

### C. Browser requests media

9. The browser requests an init segment or media segment through the selector.
10. The selector chooses an origin again using current metrics and mode.
11. The selector returns `302 Found` with a `Location` header pointing to the chosen origin.
12. The browser follows the redirect and downloads the actual media bytes from that origin.
13. The selector logs a `decision_redirect` event.

## Selector Decision Logic

Implemented in [algorithm.py](/Users/anguscheng/Desktop/multimedia-src-selection/selector/algorithm.py).

### Adaptive

The selector computes a score for each healthy origin:

```text
score = latency_weight * latency_ms
      + load_weight * load_score
      - throughput_weight * throughput_mbps
```

Lower scores win.

### Random

- choose a random healthy origin

### Round Robin

- rotate deterministically across healthy origins

## Metrics Used by the Selector

Collected by [MetricsCollector.py](/Users/anguscheng/Desktop/multimedia-src-selection/selector/MetricsCollector.py).

Per origin:

- health
- latency
- throughput
- load

Sources:

- `/health` probe
- partial media fetch for throughput estimation
- internal decaying load tracker based on recent selections

## Logging Architecture

### Persistent log

Path on selector VM:

```text
/var/log/dash-selector/requests.log
```

Format:

- JSONL
- one event per line

Main event types:

- `decision_manifest`
- `decision_redirect`
- `mode_change`
- `admin_failure`

Typical fields:

- `ts`
- `event_id`
- `event_type`
- `method`
- `path`
- `status`
- `selector_mode`
- `selected_server`
- `target`
- `decision_ms`
- `reason`
- `score`
- `scores`
- `metrics`

### In-memory recent event tail

The selector also keeps a bounded recent-event buffer in memory so the frontend can poll without rereading the entire JSONL file.

### Frontend event view

The dashboard polls:

- `/api/status` for current metrics
- `/api/logs` for recent selector events

The incident log shows human-readable summaries such as:

- `MANIFEST -> toronto [adaptive]`
- `SELECTOR -> toronto [adaptive] RTT 48.201ms load 0.00`
- `FAILURE injected -> toronto for 5s`
- `ALGORITHM switched -> random`

## API Surface

Selector endpoints:

- `/health`
- `/api/status`
- `/api/logs?limit=100&since_id=<n>`
- `/admin/mode?value=<adaptive|random|round_robin>`
- `/admin/failure?origin=<id>&duration=<seconds>`

## Deployment Flow

### Bootstrap

Origins:

- [scripts/bootstrap_origin.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/bootstrap_origin.sh)

Selector:

- [scripts/bootstrap_selector.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/bootstrap_selector.sh)

### Deploy

[scripts/deploy.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/deploy.sh):

- copies selector code to selector VM
- writes selector config
- restarts `dash-selector`
- copies DASH content to all origin VMs
- restarts NGINX on origins

## Test and Experiment Flow

### Smoke tests

- [tests/test_segments.sh](/Users/anguscheng/Desktop/multimedia-src-selection/tests/test_segments.sh)
- [tests/test_routing.sh](/Users/anguscheng/Desktop/multimedia-src-selection/tests/test_routing.sh)

### Load tests

- [scripts/run_tests.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/run_tests.sh)

Supports:

- all modes
- or a single mode argument such as `adaptive`

### Impairment injection

- [scripts/simulate_network.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/simulate_network.sh)

Uses `tc netem` on the default network interface of the target origin VM.

### Log collection and offline analysis

- [scripts/collect_logs.sh](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/collect_logs.sh)
- [scripts/parse_logs.py](/Users/anguscheng/Desktop/multimedia-src-selection/scripts/parse_logs.py)

Used to build report results such as:

- server selection counts
- average latency by server
- mode behavior under impairment
- failover timing and rerouting behavior

## Why the Selector Fetches MPDs but Redirects Segments

This is intentional.

For manifests:

- the selector fetches the MPD so it can rewrite `BaseURL`
- this keeps later requests flowing through the selector

For media segments:

- the selector redirects the client to the chosen origin
- this keeps the selector lightweight and avoids proxying all media bytes

## Current State

As implemented now:

- playback works through the selector
- selector mode switching works
- failure injection works
- live selector logs are visible in the frontend
- JSONL logs are available for report analysis

Remaining project work is mostly experiment execution and final analysis, not core architecture implementation.
