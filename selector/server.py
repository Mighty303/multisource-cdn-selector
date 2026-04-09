# This implements the actual selector server (How requests flow through our selector service)
# Job: 1) Receive HTTP requests from the client 2) Decide which origin server to use 3) Either run the MPD manifest, redirect the client to chosen segment server
# Job: 4) Log the decision
# This is the ACTUAL RUNNING SERVICE
# Classes have been split into their own files:
#   SelectorState   -> selector/SelectorState.py
#   SelectorHandler -> selector/SelectorHandler.py
from __future__ import annotations

import argparse
import json
from http.server import ThreadingHTTPServer
from pathlib import Path

from .SelectorHandler import SelectorHandler
from .SelectorState import SelectorState


# Open JSON config and return it as python dictionary
def load_config(path: Path) -> dict[str, object]:
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)

# Lets you run the server from the terminal with custom config/bind/port/log settings
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run the custom DASH selector service')
    parser.add_argument('--config', required=True, help='Path to selector JSON config')
    parser.add_argument('--bind', default='0.0.0.0', help='Bind address')
    parser.add_argument('--port', type=int, default=8080, help='Bind port')
    parser.add_argument(
        '--log-file',
        default='selector.log',
        help='Path to JSONL request log output',
    )
    return parser.parse_args()

# Main startup function
def main() -> None:
    # Parse CLI args
    args = parse_args()
    # Load config
    config = load_config(Path(args.config))
    # Create log path
    log_file = Path(args.log_file)
    # Create threaded HTTP server
    server = ThreadingHTTPServer((args.bind, args.port), SelectorHandler)
    # Attach selector state to the server
    server.selector_state = SelectorState(config, log_file)  # type: ignore[attr-defined]
    server.serve_forever()


if __name__ == '__main__':
    main()
