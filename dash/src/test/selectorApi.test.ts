import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MODE_TO_ALGORITHM, SELECTOR_BASE_URL } from '@/lib/selectorApi';

// --- SELECTOR_BASE_URL ---

describe('SELECTOR_BASE_URL', () => {
  it('is empty string when VITE_SELECTOR_BASE_URL is not set', () => {
    // import.meta.env.VITE_SELECTOR_BASE_URL is undefined in the test environment
    expect(SELECTOR_BASE_URL).toBe('');
  });
});

// --- MODE_TO_ALGORITHM ---

describe('MODE_TO_ALGORITHM', () => {
  it('maps adaptive → Latency Weighted', () => {
    expect(MODE_TO_ALGORITHM['adaptive']).toBe('Latency Weighted');
  });

  it('maps round_robin → Round Robin', () => {
    expect(MODE_TO_ALGORITHM['round_robin']).toBe('Round Robin');
  });

  it('maps random → Random', () => {
    expect(MODE_TO_ALGORITHM['random']).toBe('Random');
  });
});

// --- fetchSelectorStatus ---

describe('fetchSelectorStatus', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('returns null when SELECTOR_BASE_URL is empty (no fetch call)', async () => {
    // SELECTOR_BASE_URL is '' in the test environment
    const { fetchSelectorStatus } = await import('@/lib/selectorApi');
    const result = await fetchSelectorStatus();
    expect(result).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });
});

// --- setSelectorMode ---

describe('setSelectorMode', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('is a no-op when SELECTOR_BASE_URL is empty', async () => {
    const { setSelectorMode } = await import('@/lib/selectorApi');
    await setSelectorMode('Round Robin');
    expect(fetch).not.toHaveBeenCalled();
  });
});
