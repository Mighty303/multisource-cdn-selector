import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import type { IncidentEntry } from '@/lib/mockData';
import { SELECTOR_BASE_URL } from '@/lib/selectorApi';

interface IncidentLogProps {
  incidents: IncidentEntry[];
}

export function IncidentLog({ incidents }: IncidentLogProps) {
  const [collapsed, setCollapsed] = useState(false);

  const severityColor = (s: string) =>
    s === 'nominal' ? 'text-primary' : s === 'reroute' ? 'text-warning' : 'text-destructive';

  // Routing decision entries (from selector poll) are prefixed with "SELECTOR →"
  const isRoutingEntry = (msg: string) => msg.startsWith('SELECTOR →') || msg.startsWith('ALGORITHM');

  return (
    <div className="soc-card border-t border-border">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full px-4 py-2 flex items-center justify-between hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-primary tracking-wider">INCIDENT LOG</span>
          {/* Pulsing dot shown only when connected to a live selector */}
          {SELECTOR_BASE_URL && (
            <span className="flex items-center gap-1">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-primary" />
              </span>
              <span className="font-mono text-[9px] text-primary/70 tracking-widest">LIVE</span>
            </span>
          )}
        </div>
        {collapsed
          ? <ChevronUp className="w-4 h-4 text-muted-foreground" />
          : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
      </button>

      {!collapsed && (
        <div className="h-40 overflow-y-auto px-4 pb-3 space-y-1">
          {incidents.map(entry => (
            <div key={entry.id} className="log-entry-enter flex gap-3 text-xs font-mono">
              <span className="text-muted-foreground shrink-0">[{entry.timestamp}]</span>
              <span className={`${severityColor(entry.severity)} ${isRoutingEntry(entry.message) ? 'opacity-80' : ''}`}>
                {entry.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
