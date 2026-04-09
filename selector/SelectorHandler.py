from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from time import perf_counter
from urllib import error, parse

from .SelectorState import SelectorState


# Class handles incoming HTTP request and inherits from BaseHTTPRequestHandler
class SelectorHandler(BaseHTTPRequestHandler):
    server_version = 'DashSelector/1.0'

    # Handler can access the shared SelectorState attached to the server object
    @property
    def selector_state(self) -> SelectorState:
        return self.server.selector_state  # type: ignore[attr-defined]

    # These delegate to the same internal method
    def do_GET(self) -> None:
        self._dispatch(send_body=True)

    def do_HEAD(self) -> None:
        self._dispatch(send_body=False)

    # Core request handler
    def _dispatch(self, send_body: bool) -> None:
        started = perf_counter()
        # Parse incoming request
        parsed = parse.urlparse(self.path)

        try:
            if parsed.path == '/health':
                self._send_text(HTTPStatus.OK, 'ok', send_body)
                return

            if parsed.path == '/api/status':
                self._send_json(HTTPStatus.OK, self.selector_state.status(), send_body)
                return

            if parsed.path == '/api/logs':
                params = parse.parse_qs(parsed.query)
                limit = int(params.get('limit', ['100'])[0])
                limit = max(1, min(limit, 500))
                since_id_raw = params.get('since_id', [None])[0]
                since_id = int(since_id_raw) if since_id_raw not in (None, '') else None
                events = self.selector_state.recent_events(limit=limit, since_id=since_id)
                next_since_id = (
                    int(events[-1]['event_id'])
                    if events
                    else self.selector_state.latest_event_id()
                )
                self._send_json(
                    HTTPStatus.OK,
                    {
                        'events': events,
                        'next_since_id': next_since_id,
                    },
                    send_body,
                )
                return

            # Changes selector mode live and returns new mode as JSON
            if parsed.path == '/admin/mode':
                params = parse.parse_qs(parsed.query)
                selected_mode = params.get('value', params.get('mode', ['']))
                payload = self.selector_state.set_mode(selected_mode[0])
                self.selector_state.log_event(
                    {
                        'method': self.command,
                        'event_type': 'mode_change',
                        'request_kind': 'mode_change',
                        'timestamp': self.log_date_time_string(),
                        'client_ip': self.client_address[0],
                        'path': self.path,
                        'action': 'mode_change',
                        'status': int(HTTPStatus.OK),
                        'selector_mode': payload['mode'],
                        'target': '',
                        'decision_ms': None,
                        'reason': 'manual_mode_change',
                        'score': None,
                        'scores': {},
                        'metrics': {},
                        'previous_mode': payload.get('previous_mode'),
                    }
                )
                self._send_json(HTTPStatus.OK, payload, send_body)
                return

            # Forces an origin offline for a given duration (seconds)
            if parsed.path == '/admin/failure':
                params = parse.parse_qs(parsed.query)
                origin_vals = params.get('origin', params.get('value', []))
                origin_id = origin_vals[0] if origin_vals else ''
                valid_ids = {o.origin_id for o in self.selector_state.origins}
                if not origin_id or origin_id not in valid_ids:
                    self._send_json(HTTPStatus.BAD_REQUEST, {'error': f'unknown origin: {origin_id!r}'}, send_body)
                    return
                duration_vals = params.get('duration', ['8'])
                duration = float(duration_vals[0])
                self.selector_state.force_offline(origin_id, duration)
                self.selector_state.log_event(
                    {
                        'method': self.command,
                        'event_type': 'admin_failure',
                        'request_kind': 'admin_failure',
                        'timestamp': self.log_date_time_string(),
                        'client_ip': self.client_address[0],
                        'path': self.path,
                        'action': 'admin_failure',
                        'status': int(HTTPStatus.OK),
                        'selector_mode': self.selector_state.status()['mode'],
                        'selected_server': origin_id,
                        'target': '',
                        'decision_ms': None,
                        'reason': 'forced_offline',
                        'score': None,
                        'scores': {},
                        'metrics': {},
                        'duration_seconds': duration,
                    }
                )
                self._send_json(HTTPStatus.OK, {'origin': origin_id, 'forced_offline_seconds': duration}, send_body)
                return

            # Picks an origin and measures how long that took
            decision = self.selector_state.choose()
            elapsed_ms = round((perf_counter() - started) * 1000.0, 3)

            # If request is FOR THE MANIFEST
            if self.selector_state.is_manifest_request(parsed.path):
                # Fetch manifest from chosen origin, send it back and log the manifest action
                manifest = self.selector_state.fetch_manifest(decision, parsed.path)
                self._send_manifest(decision, manifest, send_body)
                self.selector_state.log_event(
                    self._log_payload(
                        decision=decision,
                        status=HTTPStatus.OK,
                        action='manifest',
                        elapsed_ms=elapsed_ms,
                        target=parse.urljoin(decision.origin.base_url + '/', parsed.path.lstrip('/')),
                    )
                )
                return

            # Else redirect for non manifest content (Build redirect URL to the chosen origin)
            # Whole point of having this is so selector behaves differently for MPD file (Fetch, write, respond) and segments/other files (Redirect client)
            redirect_url = self.selector_state.build_redirect_url(decision, parsed.path, parsed.query)
            # Send 302 Found code
            self.send_response(HTTPStatus.FOUND)
            self._write_common_headers(decision)
            self.send_header('Location', redirect_url)
            self.send_header('Content-Length', '0')
            self.end_headers()
            # Log redirect action
            self.selector_state.log_event(
                self._log_payload(
                    decision=decision,
                    status=HTTPStatus.FOUND,
                    action='redirect',
                    elapsed_ms=elapsed_ms,
                    target=redirect_url,
                )
            )
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {'error': str(exc)}, send_body)
        except RuntimeError as exc:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {'error': str(exc)}, send_body)
        except error.URLError as exc:
            self._send_json(HTTPStatus.BAD_GATEWAY, {'error': str(exc)}, send_body)

    # Encodes the manifest text into bytes, sends status 200 OK, writes common headers, sets DASH XML content type, sets content length, and writes the body if needed
    def _send_manifest(self, decision, manifest: str, send_body: bool) -> None:
        payload = manifest.encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self._write_common_headers(decision)
        self.send_header('Content-Type', 'application/dash+xml; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    # Converts a Python dict to pretty JSON, sends JSON response headers, and optionally writes the body.
    def _send_json(self, status: HTTPStatus, payload: dict[str, object], send_body: bool) -> None:
        encoded = json.dumps(payload, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        if send_body:
            self.wfile.write(encoded)

    # Same idea as send json but for plain text responses like /health
    def _send_text(self, status: HTTPStatus, payload: str, send_body: bool) -> None:
        encoded = payload.encode('utf-8')
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        if send_body:
            self.wfile.write(encoded)

    # Adds headers shared across manifest and redirect responses
    def _write_common_headers(self, decision) -> None:
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('X-Selector-Mode', decision.mode)
        self.send_header('X-Selector-Origin', decision.origin.origin_id)
        self.send_header('Cache-Control', 'no-store')

    # Builds dictionary that gets written to the log file
    def _log_payload(
        self,
        decision,
        status: HTTPStatus,
        action: str,
        elapsed_ms: float,
        target: str,
    ) -> dict[str, object]:
        event_type = {
            'manifest': 'decision_manifest',
            'redirect': 'decision_redirect',
        }.get(action, action)
        request_kind = 'manifest' if action == 'manifest' else 'segment'
        return {
            'method': self.command,
            'event_type': event_type,
            'request_kind': request_kind,
            'timestamp': self.log_date_time_string(),
            'client_ip': self.client_address[0],
            'path': self.path,
            'action': action,
            'status': int(status),
            'selector_mode': decision.mode,
            'selected_server': decision.origin.origin_id,
            'target': target,
            'decision_ms': elapsed_ms,
            'reason': decision.reason,
            'score': decision.score,
            'scores': decision.scores,
            'metrics': decision.metrics,
        }

    def log_message(self, format: str, *args: object) -> None:
        return
