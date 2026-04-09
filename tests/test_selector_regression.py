"""
Regression tests for the selector module after splitting into separate files.
Verifies that all imports work from new locations and from the backwards-compat
shims, and that class/function behaviour is unchanged.
"""
import math
import sys
import time
from pathlib import Path

import pytest

# Make the repo root importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Import regression — new locations
# ---------------------------------------------------------------------------

class TestImportsModels:
    def test_import_origin(self):
        from selector.models.Origin import Origin
        assert Origin

    def test_import_origin_metrics(self):
        from selector.models.OriginMetrics import OriginMetrics
        assert OriginMetrics

    def test_import_selector_weights(self):
        from selector.models.SelectorWeights import SelectorWeights
        assert SelectorWeights

    def test_import_decision(self):
        from selector.models.Decision import Decision
        assert Decision

    def test_import_probe_config(self):
        from selector.models.ProbeConfig import ProbeConfig
        assert ProbeConfig

    def test_import_models_package(self):
        from selector.models import Origin, OriginMetrics, SelectorWeights, Decision, ProbeConfig
        assert all([Origin, OriginMetrics, SelectorWeights, Decision, ProbeConfig])


class TestImportsClasses:
    def test_import_load_tracker(self):
        from selector.LoadTracker import LoadTracker
        assert LoadTracker

    def test_import_metrics_collector(self):
        from selector.MetricsCollector import MetricsCollector
        assert MetricsCollector

    def test_import_open_url(self):
        from selector.MetricsCollector import open_url
        assert open_url

    def test_import_selector_state(self):
        from selector.SelectorState import SelectorState
        assert SelectorState

    def test_import_selector_handler(self):
        from selector.SelectorHandler import SelectorHandler
        assert SelectorHandler


class TestImportsBackwardsCompat:
    """metrics.py shim must still export everything that server.py used to import."""

    def test_metrics_shim_load_tracker(self):
        from selector.metrics import LoadTracker
        assert LoadTracker

    def test_metrics_shim_metrics_collector(self):
        from selector.metrics import MetricsCollector
        assert MetricsCollector

    def test_metrics_shim_probe_config(self):
        from selector.metrics import ProbeConfig
        assert ProbeConfig

    def test_metrics_shim_open_url(self):
        from selector.metrics import open_url
        assert open_url


class TestImportsAlgorithm:
    def test_algorithm_imports_models_not_inline(self):
        """algorithm.py must import dataclasses from models, not define them."""
        import selector.algorithm as alg
        # The dataclasses should NOT be defined inside algorithm.py
        assert not hasattr(alg, '__dict__') or 'Origin' not in alg.__dict__ or \
            alg.Origin.__module__ == 'selector.models.Origin'

    def test_algorithm_exports_functions(self):
        from selector.algorithm import normalize_mode, score_origin, choose_origin
        assert all([normalize_mode, score_origin, choose_origin])


# ---------------------------------------------------------------------------
# Origin
# ---------------------------------------------------------------------------

class TestOrigin:
    def setup_method(self):
        from selector.models import Origin
        self.Origin = Origin

    def test_fields(self):
        o = self.Origin(origin_id='oregon', base_url='http://oregon.example.com', region='us-west-2')
        assert o.origin_id == 'oregon'
        assert o.base_url == 'http://oregon.example.com'
        assert o.region == 'us-west-2'

    def test_default_region(self):
        o = self.Origin(origin_id='x', base_url='http://x.example.com')
        assert o.region == ''

    def test_frozen(self):
        o = self.Origin(origin_id='x', base_url='http://x.example.com')
        with pytest.raises(Exception):
            o.origin_id = 'y'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# OriginMetrics
# ---------------------------------------------------------------------------

class TestOriginMetrics:
    def setup_method(self):
        from selector.models import OriginMetrics
        self.OriginMetrics = OriginMetrics

    def test_healthy_defaults(self):
        m = self.OriginMetrics(healthy=True)
        assert m.healthy is True
        assert m.latency_ms is None
        assert m.throughput_mbps is None
        assert m.load == 0.0
        assert m.error is None

    def test_as_dict_keys(self):
        m = self.OriginMetrics(healthy=True, latency_ms=12.5, throughput_mbps=5.0, load=1.0)
        d = m.as_dict()
        assert set(d.keys()) == {'healthy', 'latency_ms', 'throughput_mbps', 'load', 'error'}

    def test_as_dict_values(self):
        m = self.OriginMetrics(healthy=False, error='timeout')
        d = m.as_dict()
        assert d['healthy'] is False
        assert d['error'] == 'timeout'
        assert d['latency_ms'] is None


# ---------------------------------------------------------------------------
# SelectorWeights
# ---------------------------------------------------------------------------

class TestSelectorWeights:
    def setup_method(self):
        from selector.models import SelectorWeights
        self.SelectorWeights = SelectorWeights

    def test_defaults(self):
        w = self.SelectorWeights()
        assert w.latency == 0.65
        assert w.load == 0.25
        assert w.throughput == 0.10

    def test_custom(self):
        w = self.SelectorWeights(latency=0.5, load=0.3, throughput=0.2)
        assert w.latency == 0.5

    def test_frozen(self):
        w = self.SelectorWeights()
        with pytest.raises(Exception):
            w.latency = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

class TestDecision:
    def setup_method(self):
        from selector.models import Origin, Decision
        self.origin = Origin(origin_id='iowa', base_url='http://iowa.example.com')
        self.Decision = Decision

    def test_as_dict_keys(self):
        d = self.Decision(
            origin=self.origin,
            mode='adaptive',
            score=10.5,
            scores={'iowa': 10.5},
            metrics={'iowa': {'healthy': True, 'latency_ms': 10.5, 'throughput_mbps': None, 'load': 0.0, 'error': None}},
        )
        result = d.as_dict()
        assert result['origin_id'] == 'iowa'
        assert result['origin_base_url'] == 'http://iowa.example.com'
        assert result['mode'] == 'adaptive'
        assert result['score'] == 10.5


# ---------------------------------------------------------------------------
# ProbeConfig
# ---------------------------------------------------------------------------

class TestProbeConfig:
    def setup_method(self):
        from selector.models import ProbeConfig
        self.ProbeConfig = ProbeConfig

    def test_defaults(self):
        p = self.ProbeConfig()
        assert p.health_path == '/health'
        assert p.timeout_seconds == 2.0
        assert p.ttl_seconds == 5.0
        assert p.sample_bytes == 262_144

    def test_frozen(self):
        p = self.ProbeConfig()
        with pytest.raises(Exception):
            p.health_path = '/ping'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LoadTracker
# ---------------------------------------------------------------------------

class TestLoadTracker:
    def setup_method(self):
        from selector.LoadTracker import LoadTracker
        self.LoadTracker = LoadTracker

    def test_initial_snapshot_zero(self):
        lt = self.LoadTracker(['a', 'b', 'c'])
        snap = lt.snapshot()
        assert snap == {'a': 0.0, 'b': 0.0, 'c': 0.0}

    def test_mark_selected_increases_load(self):
        lt = self.LoadTracker(['a', 'b'])
        lt.mark_selected('a')
        snap = lt.snapshot()
        assert snap['a'] > 0.0
        assert snap['b'] == 0.0

    def test_load_decays_over_time(self):
        # decay_per_second=0.0 collapses load to exactly 0 after any elapsed time
        lt = self.LoadTracker(['a'], decay_per_second=0.0)
        lt.mark_selected('a')
        time.sleep(0.01)
        snap = lt.snapshot()
        assert snap['a'] == 0.0

    def test_mark_selected_accumulates(self):
        lt = self.LoadTracker(['a'])
        lt.mark_selected('a')
        lt.mark_selected('a')
        snap = lt.snapshot()
        # Two marks → load close to 2.0 (small decay between calls)
        assert snap['a'] > 1.5

    def test_snapshot_rounds_to_3dp(self):
        lt = self.LoadTracker(['x'])
        lt.mark_selected('x')
        snap = lt.snapshot()
        # Value should have at most 3 decimal places
        assert snap['x'] == round(snap['x'], 3)


# ---------------------------------------------------------------------------
# algorithm — normalize_mode
# ---------------------------------------------------------------------------

class TestNormalizeMode:
    def setup_method(self):
        from selector.algorithm import normalize_mode
        self.normalize_mode = normalize_mode

    def test_valid_modes(self):
        assert self.normalize_mode('adaptive') == 'adaptive'
        assert self.normalize_mode('random') == 'random'
        assert self.normalize_mode('round_robin') == 'round_robin'

    def test_case_insensitive(self):
        assert self.normalize_mode('ADAPTIVE') == 'adaptive'
        assert self.normalize_mode('Round_Robin') == 'round_robin'

    def test_none_defaults_to_adaptive(self):
        assert self.normalize_mode(None) == 'adaptive'

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            self.normalize_mode('least_connections')


# ---------------------------------------------------------------------------
# algorithm — score_origin
# ---------------------------------------------------------------------------

class TestScoreOrigin:
    def setup_method(self):
        from selector.algorithm import score_origin
        from selector.models import OriginMetrics, SelectorWeights
        self.score_origin = score_origin
        self.OriginMetrics = OriginMetrics
        self.weights = SelectorWeights()

    def test_unhealthy_returns_inf(self):
        m = self.OriginMetrics(healthy=False)
        assert math.isinf(self.score_origin(m, self.weights))

    def test_lower_latency_gives_lower_score(self):
        fast = self.OriginMetrics(healthy=True, latency_ms=10.0, load=0.0, throughput_mbps=0.0)
        slow = self.OriginMetrics(healthy=True, latency_ms=100.0, load=0.0, throughput_mbps=0.0)
        assert self.score_origin(fast, self.weights) < self.score_origin(slow, self.weights)

    def test_higher_throughput_gives_lower_score(self):
        fast = self.OriginMetrics(healthy=True, latency_ms=50.0, load=0.0, throughput_mbps=10.0)
        slow = self.OriginMetrics(healthy=True, latency_ms=50.0, load=0.0, throughput_mbps=1.0)
        assert self.score_origin(fast, self.weights) < self.score_origin(slow, self.weights)

    def test_none_latency_treated_as_10000(self):
        m = self.OriginMetrics(healthy=True, latency_ms=None)
        score = self.score_origin(m, self.weights)
        assert score == pytest.approx(self.weights.latency * 10_000.0)

    def test_none_throughput_treated_as_zero(self):
        m_none = self.OriginMetrics(healthy=True, latency_ms=50.0, throughput_mbps=None)
        m_zero = self.OriginMetrics(healthy=True, latency_ms=50.0, throughput_mbps=0.0)
        assert self.score_origin(m_none, self.weights) == self.score_origin(m_zero, self.weights)


# ---------------------------------------------------------------------------
# algorithm — choose_origin
# ---------------------------------------------------------------------------

class TestChooseOrigin:
    def setup_method(self):
        from selector.algorithm import choose_origin
        from selector.models import Origin, OriginMetrics, SelectorWeights
        self.choose_origin = choose_origin
        self.weights = SelectorWeights()
        self.origins = [
            Origin('a', 'http://a.example.com'),
            Origin('b', 'http://b.example.com'),
            Origin('c', 'http://c.example.com'),
        ]
        self.metrics = {
            'a': OriginMetrics(healthy=True, latency_ms=50.0, throughput_mbps=5.0),
            'b': OriginMetrics(healthy=True, latency_ms=10.0, throughput_mbps=5.0),  # best
            'c': OriginMetrics(healthy=True, latency_ms=200.0, throughput_mbps=1.0),
        }

    def test_adaptive_picks_best_score(self):
        decision, _ = self.choose_origin(
            origins=self.origins,
            metrics_by_origin=self.metrics,
            mode='adaptive',
            weights=self.weights,
            round_robin_index=0,
        )
        assert decision.origin.origin_id == 'b'

    def test_round_robin_cycles(self):
        ids = []
        idx = 0
        for _ in range(3):
            decision, idx = self.choose_origin(
                origins=self.origins,
                metrics_by_origin=self.metrics,
                mode='round_robin',
                weights=self.weights,
                round_robin_index=idx,
            )
            ids.append(decision.origin.origin_id)
        assert ids == ['a', 'b', 'c']

    def test_random_returns_healthy_origin(self):
        import random
        rng = random.Random(42)
        decision, _ = self.choose_origin(
            origins=self.origins,
            metrics_by_origin=self.metrics,
            mode='random',
            weights=self.weights,
            round_robin_index=0,
            random_source=rng,
        )
        assert decision.origin.origin_id in {'a', 'b', 'c'}

    def test_no_healthy_raises(self):
        from selector.models import OriginMetrics
        dead = {o.origin_id: OriginMetrics(healthy=False) for o in self.origins}
        with pytest.raises(RuntimeError, match='No healthy origins'):
            self.choose_origin(
                origins=self.origins,
                metrics_by_origin=dead,
                mode='adaptive',
                weights=self.weights,
                round_robin_index=0,
            )

    def test_decision_contains_all_scores(self):
        decision, _ = self.choose_origin(
            origins=self.origins,
            metrics_by_origin=self.metrics,
            mode='adaptive',
            weights=self.weights,
            round_robin_index=0,
        )
        assert set(decision.scores.keys()) == {'a', 'b', 'c'}

    def test_decision_contains_all_metrics(self):
        decision, _ = self.choose_origin(
            origins=self.origins,
            metrics_by_origin=self.metrics,
            mode='adaptive',
            weights=self.weights,
            round_robin_index=0,
        )
        assert set(decision.metrics.keys()) == {'a', 'b', 'c'}

    def test_adaptive_skips_unhealthy(self):
        from selector.models import OriginMetrics
        metrics = {
            'a': OriginMetrics(healthy=False),
            'b': OriginMetrics(healthy=False),
            'c': OriginMetrics(healthy=True, latency_ms=20.0),
        }
        decision, _ = self.choose_origin(
            origins=self.origins,
            metrics_by_origin=metrics,
            mode='adaptive',
            weights=self.weights,
            round_robin_index=0,
        )
        assert decision.origin.origin_id == 'c'


# ---------------------------------------------------------------------------
# SelectorState — construction and basic methods
# ---------------------------------------------------------------------------

class TestSelectorState:
    def setup_method(self):
        from selector.SelectorState import SelectorState
        self.SelectorState = SelectorState
        self.config = {
            'mode': 'adaptive',
            'origins': [
                {'id': 'oregon', 'base_url': 'http://oregon.example.com', 'region': 'us-west-2'},
                {'id': 'iowa', 'base_url': 'http://iowa.example.com', 'region': 'us-central1'},
            ],
            'weights': {'latency': 0.65, 'load': 0.25, 'throughput': 0.10},
            'probe': {},
        }

    def _make_state(self, config=None, log_path='/tmp/test_selector.log'):
        return self.SelectorState(config or self.config, Path(log_path))

    def test_constructs_without_error(self):
        state = self._make_state()
        assert state is not None

    def test_no_origins_raises(self):
        with pytest.raises(ValueError, match='at least one origin'):
            self._make_state({'origins': []})

    def test_set_mode_round_trip(self):
        state = self._make_state()
        result = state.set_mode('round_robin')
        assert result['mode'] == 'round_robin'

    def test_set_mode_invalid_raises(self):
        state = self._make_state()
        with pytest.raises(ValueError):
            state.set_mode('least_connections')

    def test_is_manifest_request_mpd(self):
        state = self._make_state()
        assert state.is_manifest_request('/video/stream.mpd') is True
        assert state.is_manifest_request('/video/segment.m4s') is False

    def test_is_manifest_request_configured_path(self):
        state = self._make_state()
        assert state.is_manifest_request(state.manifest_path) is True

    def test_rewrite_manifest_no_public_url(self):
        config = dict(self.config)
        config['public_base_url'] = ''
        state = self._make_state(config)
        original = '<BaseURL>http://origin.example.com/</BaseURL>'
        assert state.rewrite_manifest(original, '/manifest.mpd') == original

    def test_rewrite_manifest_rewrites_base_url(self):
        config = dict(self.config)
        config['public_base_url'] = 'http://selector.example.com'
        state = self._make_state(config)
        manifest = '<BaseURL>../segments/</BaseURL>'
        rewritten = state.rewrite_manifest(manifest, '/video/manifest.mpd')
        assert 'selector.example.com' in rewritten

    def test_build_redirect_url_appends_selector_server(self):
        from selector.models import Origin, Decision
        state = self._make_state()
        origin = Origin('oregon', 'http://oregon.example.com')
        decision = Decision(
            origin=origin,
            mode='adaptive',
            score=5.0,
            scores={'oregon': 5.0},
            metrics={},
        )
        url = state.build_redirect_url(decision, '/video/seg.m4s', '')
        assert '_selector_server=oregon' in url

    def test_log_event_writes_to_file(self, tmp_path):
        log_file = tmp_path / 'selector.log'
        state = self.SelectorState(self.config, log_file)
        state.log_event({'action': 'test', 'timestamp': '2026-01-01'})
        assert log_file.exists()
        content = log_file.read_text()
        assert '"action"' in content
