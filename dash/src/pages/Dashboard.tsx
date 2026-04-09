import { useState } from 'react';
import { Play, Square } from 'lucide-react';
import { CameraCard } from '@/components/soc/CameraCard';
import { IncidentLog } from '@/components/soc/IncidentLog';
import { Navbar } from '@/components/soc/Navbar';
import { NetworkMap } from '@/components/soc/NetworkMap';
import { algorithms } from '@/lib/mockData';
import type { Algorithm } from '@/lib/mockData';
import { useLiveData } from '@/hooks/useLiveData';

export default function Dashboard() {
  const [isPlaying, setIsPlaying] = useState(false);
  const { cameras, servers, incidents, algorithm, systemStatus, setAlgorithm, simulateFailure } = useLiveData();

  // Pick the lowest-latency non-offline server for the map active line
  const activeServer = servers
    .filter(s => s.status !== 'offline' && s.latency !== null)
    .sort((a, b) => (a.latency ?? Infinity) - (b.latency ?? Infinity))[0];
  const activeCamera = cameras[0];

  return (
    <div className="h-screen flex flex-col bg-background">
      <Navbar systemStatus={systemStatus} algorithm={algorithm} />

      <div className="flex-1 flex overflow-hidden">
        {/* LEFT: Network Map */}
        <div className="flex-1 overflow-hidden">
          <NetworkMap
            servers={servers}
            algorithm={algorithm}
            onAlgorithmChange={setAlgorithm}
            onSimulateFailure={simulateFailure}
            showControls={false}
            activeServerId={isPlaying ? activeServer?.id : undefined}
          />
        </div>

        {/* RIGHT: Control panel */}
        <div className="w-80 border-l border-border bg-card/50 overflow-y-auto p-4 space-y-5 shrink-0">

          {/* Algorithm selector */}
          <div>
            <label className="font-mono text-xs text-primary tracking-wider block mb-2">ALGORITHM</label>
            <select
              value={algorithm}
              onChange={e => setAlgorithm(e.target.value as Algorithm)}
              className="w-full bg-muted border border-border text-foreground text-xs font-mono px-3 py-2 rounded-sm focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {algorithms.map(a => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </div>

          {/* Play / Stop */}
          <button
            onClick={() => setIsPlaying(p => !p)}
            className={`w-full flex items-center justify-center gap-2 py-2 text-xs font-mono rounded-sm border transition-colors ${
              isPlaying
                ? 'border-destructive/40 text-destructive hover:bg-destructive/10'
                : 'border-primary/40 text-primary hover:bg-primary/10'
            }`}
          >
            {isPlaying ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            {isPlaying ? 'STOP' : 'START FEED'}
          </button>

          {/* Active camera feed */}
          <div>
            <label className="font-mono text-xs text-primary tracking-wider block mb-2">
              ACTIVE FEED — {activeCamera?.id ?? '—'}
            </label>
            {isPlaying && activeCamera ? (
              <div className="soc-card overflow-hidden">
                <CameraCard camera={activeCamera} onExpand={() => {}} />
              </div>
            ) : (
              <div className="aspect-video bg-background border border-border rounded-sm flex items-center justify-center grid-bg">
                <span className="font-mono text-xs text-muted-foreground tracking-wider">
                  {activeCamera ? 'PRESS START TO BEGIN' : 'NO ACTIVE SERVER'}
                </span>
              </div>
            )}
          </div>

          {/* Server metrics + failure buttons */}
          <div className="space-y-3">
            <label className="font-mono text-xs text-primary tracking-wider block">SERVER METRICS</label>
            {servers.map(server => (
              <div key={server.id} className="soc-card p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      server.status === 'online' ? 'bg-primary'
                      : server.status === 'degraded' ? 'bg-warning'
                      : 'bg-destructive'
                    }`} />
                    <span className="font-mono text-xs text-foreground">{server.name}</span>
                  </div>
                  <span className="text-[10px] text-muted-foreground">{server.jurisdiction}</span>
                </div>

                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono">
                  <span className="text-muted-foreground">RTT</span>
                  <span className={server.latency !== null && server.latency > 100 ? 'text-destructive' : 'text-foreground'}>
                    {server.latency !== null ? `${Math.round(server.latency)}ms` : '--'}
                  </span>
                  <span className="text-muted-foreground">Connections</span>
                  <span className="text-foreground">{server.connections !== null ? server.connections : '--'}</span>
                  <span className="text-muted-foreground">Bandwidth</span>
                  <span className="text-foreground">{server.bandwidth !== null ? `${Math.round(server.bandwidth)} Mbps` : '--'}</span>
                  <span className="text-muted-foreground">Loss</span>
                  <span className="text-foreground">{server.packetLoss !== null ? `${server.packetLoss.toFixed(2)}%` : '--'}</span>
                </div>

                <button
                  onClick={() => simulateFailure(server.id)}
                  disabled={server.status === 'offline'}
                  className="w-full mt-1 px-2 py-1.5 text-[10px] font-mono border border-destructive/30 text-destructive hover:bg-destructive/10 rounded-sm transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  SIMULATE FAILURE
                </button>
              </div>
            ))}
          </div>

        </div>
      </div>

      <IncidentLog incidents={incidents} />
    </div>
  );
}
