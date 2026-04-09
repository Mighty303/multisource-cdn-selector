import { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Navbar } from '@/components/soc/Navbar';
import { MetricsLineChart, MetricsBarChart } from '@/components/soc/MetricsChart';
import { useLiveData } from '@/hooks/useLiveData';
import { SELECTOR_BASE_URL } from '@/lib/selectorApi';

const serverColors = ['#00ff88', '#0ea5e9', '#f59e0b'];

// Shape for a single latency history data point
interface LatencyPoint extends Record<string, unknown> {
  time: string;
  Oregon: number | null;
  Toronto: number | null;
  'N. California': number | null;
}

export default function Analytics() {
  const { servers, incidents, algorithm, systemStatus } = useLiveData();
  const [timeRange, setTimeRange] = useState('15min');
  const [latencyHistory, setLatencyHistory] = useState<LatencyPoint[]>([]);
  const latencyHistoryRef = useRef<LatencyPoint[]>([]);

  // Accumulate real latency readings from live server state every 5 s
  useEffect(() => {
    const push = () => {
      const oregon      = servers.find(s => s.id === 'oregon');
      const toronto     = servers.find(s => s.id === 'toronto');
      const ncalifornia = servers.find(s => s.id === 'ncalifornia');

      // Only record a point when at least one origin has live data
      if (!oregon?.latency && !toronto?.latency && !ncalifornia?.latency) return;

      const point: LatencyPoint = {
        time: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' }),
        Oregon:          oregon?.latency      ?? null,
        Toronto:         toronto?.latency     ?? null,
        'N. California': ncalifornia?.latency ?? null,
      };

      const updated = [...latencyHistoryRef.current, point].slice(-30);
      latencyHistoryRef.current = updated;
      setLatencyHistory(updated);
    };

    push();
    const id = setInterval(push, 5000);
    return () => clearInterval(id);
  // servers intentionally excluded — we want a stable interval, not a re-subscribe on every jitter tick
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Server load bar chart data derived from live connections/load
  const serverLoadData = servers.map(s => ({
    name: s.name,
    load: s.connections !== null ? s.connections * 10 : 0,
    connections: s.connections ?? 0,
  }));

  // Routing decisions from the live incident log (SELECTOR → entries)
  const routingDecisions = incidents.filter(e => e.message.startsWith('SELECTOR →'));

  // Stat cards derived from live data
  const reroutes = incidents.filter(e => e.severity === 'reroute').length;
  const activeFeeds = 6;

  const TrendIcon = ({ trend }: { trend: 'up' | 'down' | 'flat' }) =>
    trend === 'up' ? <TrendingUp className="w-3 h-3 text-primary" /> :
    trend === 'down' ? <TrendingDown className="w-3 h-3 text-destructive" /> :
    <Minus className="w-3 h-3 text-muted-foreground" />;

  const statCards = [
    { label: 'ACTIVE FEEDS',  value: activeFeeds.toString(),  trend: 'flat' as const },
    { label: 'REROUTES',      value: reroutes.toString(),     trend: reroutes > 0 ? 'up' as const : 'flat' as const },
    { label: 'SELECTOR MODE', value: algorithm.toUpperCase(), trend: 'flat' as const },
    { label: 'LIVE DATA',     value: SELECTOR_BASE_URL ? 'CONNECTED' : 'SIMULATED', trend: SELECTOR_BASE_URL ? 'up' as const : 'flat' as const },
  ];

  return (
    <div className="h-screen flex flex-col bg-background">
      <Navbar systemStatus={systemStatus} algorithm={algorithm} />

      <div className="flex-1 overflow-y-auto p-6 grid-bg space-y-6">
        {/* Time range */}
        <div className="flex items-center gap-2">
          {['5min', '15min', '1hr'].map(r => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-3 py-1 text-xs font-mono rounded-sm transition-colors ${
                timeRange === r ? 'bg-primary/10 text-primary border border-primary/30' : 'text-muted-foreground border border-border hover:text-foreground'
              }`}
            >
              {r.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-4 gap-4">
          {statCards.map(card => (
            <div key={card.label} className="soc-card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono text-muted-foreground tracking-wider">{card.label}</span>
                <TrendIcon trend={card.trend} />
              </div>
              <span className="font-mono text-2xl text-foreground">{card.value}</span>
            </div>
          ))}
        </div>

        {/* Server load + Latency */}
        <div className="grid grid-cols-2 gap-4">
          <div className="soc-card p-4">
            <h3 className="font-mono text-xs text-primary tracking-wider mb-4">SERVER LOAD (connections × 10)</h3>
            <div className="h-56">
              {serverLoadData.some(d => d.load > 0) ? (
                <MetricsBarChart data={serverLoadData} bars={[{ key: 'load', color: '#00ff88' }]} />
              ) : (
                <div className="h-full flex items-center justify-center text-xs font-mono text-muted-foreground">
                  WAITING FOR LIVE DATA…
                </div>
              )}
            </div>
          </div>
          <div className="soc-card p-4">
            <h3 className="font-mono text-xs text-primary tracking-wider mb-4">LATENCY OVER TIME (ms)</h3>
            <div className="h-56">
              {latencyHistory.length > 1 ? (
                <MetricsLineChart
                  data={latencyHistory}
                  lines={['Oregon', 'Toronto', 'N. California'].map((s, i) => ({ key: s, color: serverColors[i] }))}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-xs font-mono text-muted-foreground">
                  WAITING FOR LIVE DATA…
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Live routing decision log */}
        <div className="soc-card p-4">
          <h3 className="font-mono text-xs text-primary tracking-wider mb-4">
            ROUTING DECISION LOG
            {SELECTOR_BASE_URL && (
              <span className="ml-3 text-primary/60">● LIVE</span>
            )}
          </h3>
          {routingDecisions.length === 0 ? (
            <div className="text-xs font-mono text-muted-foreground py-4 text-center">
              WAITING FOR ROUTING DECISIONS…
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="text-left py-2 px-3">TIMESTAMP</th>
                    <th className="text-left py-2 px-3">SELECTED ORIGIN</th>
                    <th className="text-left py-2 px-3">MODE</th>
                    <th className="text-left py-2 px-3">RTT</th>
                    <th className="text-left py-2 px-3">LOAD</th>
                  </tr>
                </thead>
                <tbody>
                  {routingDecisions.map((entry) => {
                    // Parse: "SELECTOR → <origin> [<mode>] RTT <n>ms load <n>"
                    const originMatch = entry.message.match(/SELECTOR → (\S+)/);
                    const modeMatch   = entry.message.match(/\[([^\]]+)\]/);
                    const rttMatch    = entry.message.match(/RTT ([\d.]+)ms/);
                    const loadMatch   = entry.message.match(/load ([\d.]+)/);
                    return (
                      <tr key={entry.id} className={`border-b border-border/50 hover:bg-muted/20 ${entry.severity === 'reroute' ? 'text-warning' : ''}`}>
                        <td className="py-2 px-3 text-muted-foreground">{entry.timestamp}</td>
                        <td className="py-2 px-3 text-primary">{originMatch?.[1] ?? '—'}</td>
                        <td className="py-2 px-3 text-foreground">{modeMatch?.[1] ?? '—'}</td>
                        <td className="py-2 px-3 text-foreground">{rttMatch ? `${rttMatch[1]}ms` : '—'}</td>
                        <td className="py-2 px-3 text-foreground">{loadMatch?.[1] ?? '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
