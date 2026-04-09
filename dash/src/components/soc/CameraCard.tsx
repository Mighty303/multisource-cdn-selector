import { useEffect, useRef } from 'react';
import { Maximize2 } from 'lucide-react';
import * as dashjs from 'dashjs';
import type { Camera } from '@/lib/mockData';

interface CameraCardProps {
  camera: Camera;
  onExpand: (id: string) => void;
}

export function CameraCard({ camera, onExpand }: CameraCardProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<dashjs.MediaPlayerClass | null>(null);
  const statusColor = camera.status === 'online' ? 'bg-primary' : camera.status === 'warning' ? 'bg-warning' : 'bg-destructive';

  useEffect(() => {
    if (!videoRef.current || !camera.mpdUrl) return;

    const player = dashjs.MediaPlayer().create();
    player.initialize(videoRef.current, camera.mpdUrl, true);
    player.updateSettings({ streaming: { abr: { autoSwitchBitrate: { video: true } } } });
    player.on(dashjs.MediaPlayer.events.PLAYBACK_ENDED, () => {
      player.seek(0);
      player.play();
    });
    playerRef.current = player;

    return () => {
      player.destroy();
      playerRef.current = null;
    };
  }, [camera.mpdUrl]);

  return (
    <div
      className="soc-card overflow-hidden cursor-pointer group transition-all duration-300"
      onClick={() => onExpand(camera.id)}
    >
      {/* Feed Area */}
      <div className="relative aspect-video bg-background overflow-hidden">
        <video
          ref={videoRef}
          className="w-full h-full object-cover"
          muted
          playsInline
        />

        {/* Top-left overlay */}
        <div className="absolute top-2 left-2 flex items-center gap-2 bg-background/80 p-3 rounded-full">
          <span className={`w-2 h-2 rounded-full ${statusColor}`} />
          <span className="font-mono text-xs text-foreground/80">{camera.id}</span>
          <span className="text-xs text-muted-foreground">{camera.location}</span>
        </div>

        {/* Top-right REC indicator */}
        <div className="absolute top-2 right-2 flex items-center p-3 gap-1.5">
          <span className="w-2 h-2 rounded-full bg-destructive rec-dot" />
          <span className="font-mono text-xs text-destructive">REC</span>
        </div>

        {/* Expand icon */}
        <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <Maximize2 className="w-4 h-4 text-foreground/50" />
        </div>
      </div>

      {/* Bottom stats bar */}
      <div className="px-3 py-2 border-t border-border flex items-center gap-3 text-[10px] font-mono text-muted-foreground flex-wrap">
        <span>BITRATE: <span className="text-foreground">{camera.bitrate !== null ? `${camera.bitrate.toFixed(1)} Mbps` : '--'}</span></span>
        <span>LATENCY: <span className={camera.latency !== null && camera.latency > 50 ? 'text-warning' : 'text-foreground'}>{camera.latency !== null ? `${Math.round(camera.latency)}ms` : '--'}</span></span>
        <span>LOSS:<span className={camera.packetLoss !== null && camera.packetLoss > 0.2 ? 'text-warning' : 'text-foreground'}>{camera.packetLoss !== null ? `${camera.packetLoss.toFixed(1)}%` : '--'}</span></span>
      </div>
    </div>
  );
}
