import { X, Camera as CameraIcon } from 'lucide-react';
import type { Camera } from '@/lib/mockData';

interface ExpandedCameraProps {
  camera: Camera;
  onClose: () => void;
}

export function ExpandedCamera({ camera, onClose }: ExpandedCameraProps) {
  return (
    <div className="fixed inset-0 z-50 bg-background/95 flex" onClick={onClose}>
      <div className="flex-1 flex items-center justify-center" onClick={e => e.stopPropagation()}>
        <div className="relative w-full max-w-5xl aspect-video bg-background grid-bg flex items-center justify-center border border-border rounded-sm">
          <div className="flex flex-col items-center gap-3 opacity-40">
            <CameraIcon className="w-16 h-16 text-primary" />
            <span className="font-mono text-sm text-primary tracking-widest">FEED ACTIVE — {camera.id}</span>
          </div>

          <div className="absolute top-3 left-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary" />
            <span className="font-mono text-sm text-foreground">{camera.id} — {camera.location}</span>
          </div>

          <div className="absolute top-3 right-3 flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-destructive rec-dot" />
              <span className="font-mono text-xs text-destructive">REC</span>
            </div>
            <button onClick={onClose} className="p-1 hover:bg-muted rounded-sm transition-colors">
              <X className="w-5 h-5 text-foreground" />
            </button>
          </div>
        </div>
      </div>

      {/* Stats sidebar */}
      <div className="w-72 border-l border-border bg-card p-4 space-y-4 overflow-y-auto" onClick={e => e.stopPropagation()}>
        <h3 className="font-mono text-sm text-primary tracking-wider">FEED DETAILS</h3>
        {[
          ['Camera', camera.id],
          ['Location', camera.location],
          ['Status', camera.status.toUpperCase()],
          ['Bitrate', `${camera.bitrate.toFixed(1)} Mbps`],
          ['Latency', `${Math.round(camera.latency)}ms`],
          ['Packet Loss', `${camera.packetLoss.toFixed(2)}%`],
        ].map(([label, value]) => (
          <div key={label} className="flex justify-between items-center border-b border-border/50 pb-2">
            <span className="text-xs text-muted-foreground">{label}</span>
            <span className="font-mono text-xs text-foreground">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
