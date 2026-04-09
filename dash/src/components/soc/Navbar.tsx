import { Link, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import type { Algorithm } from '@/lib/mockData';

interface NavbarProps {
  systemStatus: 'nominal' | 'warning' | 'critical';
  algorithm: Algorithm;
}

export function Navbar({ systemStatus, algorithm }: NavbarProps) {
  const location = useLocation();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const statusText = systemStatus === 'nominal' ? 'NETWORK NOMINAL' : systemStatus === 'warning' ? 'NETWORK WARNING' : 'NETWORK CRITICAL';
  const statusColor = systemStatus === 'nominal' ? 'text-primary' : systemStatus === 'warning' ? 'text-warning' : 'text-destructive';

  const navLinks = [
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/analytics', label: 'Analytics' },
  ];

  return (
    <nav className="h-12 border-b border-border bg-card/80 backdrop-blur-sm flex items-center px-4 justify-between shrink-0 z-50">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary pulse-dot" />
          <span className="font-mono text-sm font-semibold text-foreground tracking-wider">SecureStream</span>
        </div>

        <div className="flex items-center gap-1 ml-4">
          {navLinks.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className={`px-3 py-1.5 text-xs font-medium rounded-sm transition-colors ${
                location.pathname === link.path
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className={`w-1.5 h-1.5 rounded-full ${statusColor.replace('text-', 'bg-')}`} />
        <span className={`font-mono text-xs tracking-wider ${statusColor}`}>{statusText}</span>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-[10px] font-mono px-2 py-1 bg-secondary/10 text-secondary rounded-sm">
          {algorithm.toUpperCase().replace(/ /g, '-')}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {time.toLocaleTimeString('en-US', { hour12: false })}
        </span>
      </div>
    </nav>
  );
}
