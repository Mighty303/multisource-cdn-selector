import type { Camera, ServerNode } from '@/lib/mockData';

interface DashboardSidebarProps {
  cameras: Camera[];
  servers: ServerNode[];
}

export function DashboardSidebar({ cameras, servers }: DashboardSidebarProps) {
  const statusDot = (status: string) =>
    status === 'online' ? 'bg-primary' : status === 'warning' || status === 'degraded' ? 'bg-warning' : 'bg-destructive';

  return (
    <aside className="w-60 shrink-0 border-r border-border bg-card/50 flex flex-col h-full overflow-hidden">
      <div className="px-4 py-3 border-b border-border">
        <span className="font-mono text-xs text-primary tracking-wider">CAMERA FEEDS</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {cameras.map(cam => (
          <div key={cam.id} className="px-4 py-2.5 border-b border-border/50 hover:bg-muted/30 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full ${statusDot(cam.status)}`} />
                <span className="font-mono text-xs text-foreground">{cam.name}</span>
              </div>
              <span className="text-[10px] font-mono text-muted-foreground">{cam.region}</span>
            </div>
            <span className="text-[10px] text-muted-foreground ml-3.5">{cam.location}</span>
          </div>
        ))}
      </div>

      <div className="border-t border-border px-4 py-3 space-y-2">
        <span className="font-mono text-xs text-primary tracking-wider">SERVER HEALTH</span>
        {servers.map(srv => (
          <div key={srv.id} className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${statusDot(srv.status)}`} />
              <span className="text-xs text-foreground">{srv.name}</span>
            </div>
            <span className={`font-mono text-xs ${srv.latency === null ? 'text-muted-foreground' : srv.latency > 100 ? 'text-destructive' : srv.latency > 40 ? 'text-warning' : 'text-primary'}`}>
              {srv.latency !== null ? `${Math.round(srv.latency)}ms` : '--'}
            </span>
          </div>
        ))}
      </div>
    </aside>
  );
}
