import React from 'react';
import { Log } from '@/types';
import { Badge } from '@/components/ui/Badge';

export const ActivityFeed: React.FC<{ logs: Log[] }> = ({ logs }) => {
  const levelBadge = (level: string) => {
    switch (level) {
      case 'ERROR':
      case 'CRITICAL':
        return <Badge variant="danger">ERROR</Badge>;
      case 'WARNING':
        return <Badge variant="warning">WARN</Badge>;
      default:
        return <Badge variant="info">INFO</Badge>;
    }
  };

  return (
    <div className="space-y-3">
      {logs.length === 0 ? (
        <p className="text-xs text-slate-500 py-4 text-center">No recent activity logs</p>
      ) : (
        logs.map((log) => (
          <div
            key={log.id}
            className="flex items-start justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:bg-slate-800/40 transition"
          >
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5">{levelBadge(log.level)}</div>
              <div>
                <p className="text-xs text-slate-200 font-medium leading-relaxed">{log.message}</p>
                <span className="text-[10px] text-slate-500 mt-1 block font-mono">
                  {new Date(log.timestamp).toLocaleTimeString()} {log.module ? `• ${log.module}` : ''}
                </span>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
