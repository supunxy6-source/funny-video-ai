import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: string;
  icon: string;
  trend?: 'up' | 'down' | 'neutral';
}

export const KPICard: React.FC<KPICardProps> = ({ title, value, change, icon, trend = 'neutral' }) => {
  const trendColors = {
    up: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    down: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    neutral: 'text-slate-400 bg-slate-800 border-slate-700',
  };

  return (
    <div className="glass-card rounded-2xl p-5 border border-slate-800 hover:border-slate-700 transition duration-300">
      <div className="flex items-center justify-between">
        <span className="text-2xl">{icon}</span>
        {change && (
          <span className={`text-xs px-2 py-0.5 rounded-full border ${trendColors[trend]}`}>
            {change}
          </span>
        )}
      </div>
      <div className="mt-4">
        <h3 className="text-3xl font-extrabold text-slate-100 tracking-tight">{value}</h3>
        <p className="text-xs text-slate-400 font-medium mt-1">{title}</p>
      </div>
    </div>
  );
};
