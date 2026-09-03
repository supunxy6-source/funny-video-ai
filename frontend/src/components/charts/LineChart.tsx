import React from 'react';

interface DataPoint {
  label: string;
  value: number;
}

export const LineChart: React.FC<{ data: DataPoint[]; height?: number }> = ({ data, height = 200 }) => {
  if (!data || data.length === 0) {
    return <div className="h-48 flex items-center justify-center text-slate-500 text-xs">No chart data</div>;
  }

  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const points = data
    .map((d, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - (d.value / maxValue) * 80 - 10;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="w-full relative" style={{ height }}>
      <svg className="w-full h-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <linearGradient id="chartGlow" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
          </linearGradient>
        </defs>

        <polygon points={`0,100 ${points} 100,100`} fill="url(#chartGlow)" />
        <polyline fill="none" stroke="#38bdf8" strokeWidth="2.5" points={points} vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="flex justify-between text-[10px] text-slate-500 mt-2">
        {data.map((d, i) => (
          <span key={i}>{d.label}</span>
        ))}
      </div>
    </div>
  );
};
