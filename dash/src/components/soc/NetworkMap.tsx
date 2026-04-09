import { useState } from 'react';
import type { ServerNode, Algorithm } from '@/lib/mockData';
import { algorithms } from '@/lib/mockData';

interface NetworkMapProps {
  servers: ServerNode[];
  algorithm: Algorithm;
  onAlgorithmChange: (a: Algorithm) => void;
  onSimulateFailure: (serverId: string) => void;
  showControls?: boolean;
  activeServerId?: string;
}

// Simplified world map path
// Simplified North America outline — West Coast (left) through Canada/East (right)
const WORLD_PATH = "M 80 100 Q 100 70 130 65 L 155 60 Q 175 55 195 70 L 210 90 Q 220 115 210 140 L 195 165 Q 180 185 165 200 L 145 220 Q 125 235 110 220 L 95 200 Q 75 175 70 150 L 68 125 Q 70 110 80 100 Z M 195 65 Q 270 35 370 45 L 430 50 Q 480 55 530 70 L 580 80 Q 630 90 640 105 L 645 125 Q 645 145 625 155 L 600 160 Q 565 170 530 160 L 480 148 Q 430 138 390 125 L 350 112 Q 290 100 240 95 L 210 92 Z M 350 115 Q 380 108 410 112 L 430 120 Q 445 132 440 150 L 430 168 Q 415 185 390 188 L 365 185 Q 340 178 332 160 L 328 140 Q 330 122 350 115 Z";

// Server positions on map (projected).
// IDs must match the origin IDs in scripts/env.example (ORIGIN_VMS).
const serverPositions: Record<string, { x: number; y: number }> = {
  oregon:      { x: 175, y: 150 },
  ncalifornia: { x: 150, y: 215 },
  toronto:     { x: 590, y: 110 },
};

const clientPos = { x: 390, y: 42 };
const iowaSelectorPos = { x: 370, y: 152 };
const SELECTOR_BASE_URL = import.meta.env.VITE_SELECTOR_BASE_URL as string | undefined;

export function NetworkMap({ servers, algorithm, onAlgorithmChange, onSimulateFailure, showControls = true, activeServerId }: NetworkMapProps) {
  const [localActiveServer, setLocalActiveServer] = useState<string>('toronto');
  // When showControls=false the parent fully controls activeServerId; don't fall back to local state.
  const resolvedActiveServer = showControls ? (activeServerId ?? localActiveServer) : activeServerId;

  const getServerColor = (s: ServerNode) =>
    s.status === 'online' ? '#00ff88' : s.status === 'degraded' ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex h-full">
      {/* Map */}
      <div className="flex-1 relative grid-bg flex items-center justify-center overflow-hidden">
        <svg viewBox="0 0 800 280" className="w-full max-w-5xl">
          {/* World outline */}
          <path d={WORLD_PATH} fill="hsl(150, 10%, 12%)" stroke="hsl(150, 20%, 20%)" strokeWidth="0.5" />

          {/* Connection lines */}
          {servers.map(server => {
            const pos = serverPositions[server.id];
            if (!pos) return null;
            const isActive = server.id === resolvedActiveServer && server.status !== 'offline';
            return (
              <line
                key={server.id}
                x1={iowaSelectorPos.x} y1={iowaSelectorPos.y}
                x2={pos.x} y2={pos.y}
                stroke={isActive ? '#00ff88' : 'hsl(150, 20%, 20%)'}
                strokeWidth={isActive ? 2 : 0.8}
                className={isActive ? 'data-flow-line' : ''}
                opacity={isActive ? 0.8 : 0.3}
              />
            );
          })}

          {/* Client node */}
          <circle cx={clientPos.x} cy={clientPos.y} r="8" fill="#0ea5e9" opacity="0.8" />
          <circle cx={clientPos.x} cy={clientPos.y} r="14" fill="none" stroke="#0ea5e9" strokeWidth="0.8" opacity="0.4" />
          <text x={clientPos.x} y={clientPos.y - 16} textAnchor="middle" fill="#0ea5e9" fontSize="8" fontFamily="monospace">CLIENT</text>

          {/* Iowa selector node */}
          <line
            x1={clientPos.x} y1={clientPos.y}
            x2={iowaSelectorPos.x} y2={iowaSelectorPos.y}
            stroke="#a855f7" strokeWidth="1" opacity="0.5" strokeDasharray="3 2"
          />
          <g transform={`translate(${iowaSelectorPos.x}, ${iowaSelectorPos.y})`}>
            <rect x="-7" y="-7" width="14" height="14" fill="#a855f7" opacity="0.85" transform="rotate(45)" />
            {SELECTOR_BASE_URL && (
              <circle r="14" fill="none" stroke="#a855f7" strokeWidth="0.8" opacity="0.4">
                <animate attributeName="r" values="14;22;14" dur="3s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.4;0;0.4" dur="3s" repeatCount="indefinite" />
              </circle>
            )}
            <text y="22" textAnchor="middle" fill="#a855f7" fontSize="8" fontFamily="monospace">SELECTOR</text>
            <text y="31" textAnchor="middle" fill="#a855f7" fontSize="8" fontFamily="monospace">IOWA</text>
          </g>

          {/* Server nodes */}
          {servers.map(server => {
            const pos = serverPositions[server.id];
            if (!pos) return null;
            const color = getServerColor(server);
            return (
              <g key={server.id} onClick={() => setLocalActiveServer(server.id)} className="cursor-pointer">
                <circle cx={pos.x} cy={pos.y} r="16" fill={color} opacity="0.2" />
                <circle cx={pos.x} cy={pos.y} r="8" fill={color} opacity="0.9" />
                {server.status === 'online' && (
                  <circle cx={pos.x} cy={pos.y} r="20" fill="none" stroke={color} strokeWidth="0.8" opacity="0.3">
                    <animate attributeName="r" values="20;32;20" dur="3s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.3;0;0.3" dur="3s" repeatCount="indefinite" />
                  </circle>
                )}
                <text x={pos.x} y={pos.y + 24} textAnchor="middle" fill={color} fontSize="8" fontFamily="monospace">
                  {server.name.toUpperCase()}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Sidebar */}
      {showControls && <div className="w-80 border-l border-border bg-card/50 overflow-y-auto p-4 space-y-5">
        <div>
          <label className="font-mono text-xs text-primary tracking-wider block mb-2">ALGORITHM</label>
          <select
            value={algorithm}
            onChange={e => onAlgorithmChange(e.target.value as Algorithm)}
            className="w-full bg-muted border border-border text-foreground text-xs font-mono px-3 py-2 rounded-sm focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {algorithms.map(a => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>

        {servers.map(server => (
          <div key={server.id} className="soc-card p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${server.status === 'online' ? 'bg-primary' : server.status === 'degraded' ? 'bg-warning' : 'bg-destructive'}`} />
                <span className="font-mono text-xs text-foreground">{server.name}</span>
              </div>
              <span className="text-[10px] text-muted-foreground">{server.jurisdiction}</span>
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono">
              <span className="text-muted-foreground">RTT</span>
              <span className={server.latency !== null && server.latency > 100 ? 'text-destructive' : 'text-foreground'}>{server.latency !== null ? `${Math.round(server.latency)}ms` : '--'}</span>
              <span className="text-muted-foreground">Connections</span>
              <span className="text-foreground">{server.connections !== null ? server.connections : '--'}</span>
              <span className="text-muted-foreground">Bandwidth</span>
              <span className="text-foreground">{server.bandwidth !== null ? `${Math.round(server.bandwidth)} Mbps` : '--'}</span>
              <span className="text-muted-foreground">Loss</span>
              <span className="text-foreground">{server.packetLoss !== null ? `${server.packetLoss.toFixed(2)}%` : '--'}</span>
            </div>

            <button
              onClick={() => onSimulateFailure(server.id)}
              disabled={server.status === 'offline'}
              className="w-full mt-1 px-2 py-1.5 text-[10px] font-mono border border-destructive/30 text-destructive hover:bg-destructive/10 rounded-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              SIMULATE FAILURE
            </button>
          </div>
        ))}
      </div>}
    </div>
  );
}
