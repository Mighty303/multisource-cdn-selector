import { describe, it, expect } from 'vitest';
import {
  initialCameras,
  initialServers,
  algorithms,
  randomVariation,
} from '@/lib/mockData';

describe('initialServers', () => {
  it('has three servers', () => {
    expect(initialServers).toHaveLength(3);
  });

  it('uses the correct VM origin IDs (matching env.example ORIGIN_VMS)', () => {
    const ids = initialServers.map(s => s.id);
    expect(ids).toContain('oregon');
    expect(ids).toContain('toronto');
    expect(ids).toContain('ncalifornia');
  });

  it('does not contain the old virginia server', () => {
    expect(initialServers.find(s => s.id === 'virginia')).toBeUndefined();
  });

  it('has distinct region strings', () => {
    const regions = initialServers.map(s => s.region);
    expect(new Set(regions).size).toBe(regions.length);
  });
});

describe('initialCameras', () => {
  it('has six cameras', () => {
    expect(initialCameras).toHaveLength(6);
  });

  it('mpdUrl falls back to /dash_content/clipN/manifest.mpd when selector is not configured', () => {
    // VITE_SELECTOR_BASE_URL is unset in test env → SELECTOR_BASE_URL === ''
    initialCameras.forEach((cam, i) => {
      expect(cam.mpdUrl).toBe(`/dash_content/clip${i + 1}/manifest.mpd`);
    });
  });
});

describe('algorithms', () => {
  it('includes all four algorithm options', () => {
    expect(algorithms).toContain('Round Robin');
    expect(algorithms).toContain('Latency Weighted');
    expect(algorithms).toContain('Load Balanced');
    expect(algorithms).toContain('Random');
  });
});

describe('randomVariation', () => {
  it('returns a value within range', () => {
    for (let i = 0; i < 50; i++) {
      const result = randomVariation(100, 10);
      expect(result).toBeGreaterThanOrEqual(95);
      expect(result).toBeLessThanOrEqual(105);
    }
  });
});

describe('initialServers names', () => {
  it('uses N. California instead of Virginia', () => {
    const names = initialServers.map(s => s.name);
    expect(names).toContain('N. California');
    expect(names).not.toContain('Virginia');
  });

  it('all numeric metrics start as null (loading state)', () => {
    initialServers.forEach(s => {
      expect(s.latency).toBeNull();
      expect(s.connections).toBeNull();
      expect(s.bandwidth).toBeNull();
      expect(s.packetLoss).toBeNull();
    });
  });
});
