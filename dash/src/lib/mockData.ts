import { SELECTOR_BASE_URL } from '@/lib/selectorApi';

export interface Camera {
  id: string;
  name: string;
  location: string;
  region: string;
  status: 'online' | 'warning' | 'offline';
  bitrate: number | null;
  latency: number | null;
  packetLoss: number | null;
  mpdUrl: string;
}

export interface ServerNode {
  id: string;
  name: string;
  region: string;
  location: string;
  lat: number;
  lng: number;
  latency: number | null;
  connections: number | null;
  bandwidth: number | null;
  packetLoss: number | null;
  jurisdiction: string;
  status: 'online' | 'degraded' | 'offline';
}

export interface IncidentEntry {
  id: string;
  timestamp: string;
  message: string;
  severity: 'nominal' | 'reroute' | 'failure';
  camera?: string;
}

export interface RoutingLog {
  timestamp: string;
  camera: string;
  fromServer: string;
  toServer: string;
  reason: string;
  latencyDelta: string;
}

// Build the MPD URL for a camera clip.
// When the selector is configured, each camera routes through the selector at its clip MPD path.
// Without a selector URL, fall back to the local FastAPI static path for development.
function mpdUrl(clipIndex: number): string {
  return SELECTOR_BASE_URL
    ? `${SELECTOR_BASE_URL}/video/dash_content/clip${clipIndex}/manifest.mpd`
    : `/dash_content/clip${clipIndex}/manifest.mpd`;
}

export const initialCameras: Camera[] = [
  { id: 'CAM-01', name: 'CAM-01', location: 'Toronto CA',    region: 'ca-central-1', status: 'online',  bitrate: null, latency: null, packetLoss: null, mpdUrl: mpdUrl(1) },
  { id: 'CAM-02', name: 'CAM-02', location: 'New York US',   region: 'us-west-2',    status: 'online',  bitrate: null, latency: null, packetLoss: null, mpdUrl: mpdUrl(2) },
  { id: 'CAM-03', name: 'CAM-03', location: 'Vancouver CA',  region: 'us-west-1',    status: 'online',  bitrate: null, latency: null, packetLoss: null, mpdUrl: mpdUrl(3) },
  { id: 'CAM-04', name: 'CAM-04', location: 'Montreal CA',   region: 'ca-central-1', status: 'warning', bitrate: null, latency: null, packetLoss: null, mpdUrl: mpdUrl(4) },
  { id: 'CAM-05', name: 'CAM-05', location: 'Chicago US',    region: 'us-west-2',    status: 'online',  bitrate: null, latency: null, packetLoss: null, mpdUrl: mpdUrl(5) },
  { id: 'CAM-06', name: 'CAM-06', location: 'Portland US',   region: 'us-west-1',    status: 'online',  bitrate: null, latency: null, packetLoss: null, mpdUrl: mpdUrl(6) },
];

// Server IDs match the origin IDs configured in scripts/env.example (ORIGIN_VMS / ORIGIN_ENDPOINTS).
// Numeric metrics start null — filled in on the first selector poll (~5 s after mount).
export const initialServers: ServerNode[] = [
  { id: 'oregon',      name: 'Oregon',        region: 'us-west-1',    location: 'Portland, OR',    lat: 45.52, lng: -122.68, latency: null, connections: null, bandwidth: null, packetLoss: null, jurisdiction: 'US-West', status: 'online' },
  { id: 'toronto',     name: 'Toronto',       region: 'ca-central-1', location: 'Toronto, ON',     lat: 43.65, lng: -79.38,  latency: null, connections: null, bandwidth: null, packetLoss: null, jurisdiction: 'CA-East', status: 'online' },
  { id: 'ncalifornia', name: 'N. California', region: 'us-west-2',    location: 'Santa Clara, CA', lat: 37.35, lng: -121.97, latency: null, connections: null, bandwidth: null, packetLoss: null, jurisdiction: 'US-West', status: 'online' },
];

export const algorithms = ['Round Robin', 'Latency Weighted', 'Load Balanced', 'Random'] as const;
export type Algorithm = typeof algorithms[number];

// Start with no incidents — live entries are appended by useLiveData on each selector poll.
export const initialIncidents: IncidentEntry[] = [];

export function randomVariation(base: number, range: number): number {
  return Math.round((base + (Math.random() - 0.5) * range) * 10) / 10;
}
