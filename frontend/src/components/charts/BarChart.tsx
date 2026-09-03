import React from 'react';

interface DataPoint {
  label: string;
  value: number;
}

export const BarChart: React.FC<{ data: DataPoint[]; height?: number }> = ({ data, height = 200 }) => {
  if (!data || data.length === 0) {
    return <div className="h-48 flex items-center justify-center text-slate-500 text-xs">No chart data</div>;
  }

  const maxValue = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="w-full flex items-end justify-between gap-2 px-2" style={{ height }}>
      {data.map((item, idx) => {
        const heightPct = Math.max((item.value / maxValue) * 100, 5);
        return (
          <div key={idx} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
            <div
              className="w-full bg-gradient-to-t from-indigo-600 to-sky-400 rounded-t-md transition-all duration-300 group-hover:brightness-125"
              style={{ height: `${heightPct}%` }}
            ></div>
            <span className="text-[10px] text-slate-400 font-medium truncate w-full text-center">
              {item.label}
            </span>
          </div>
        );
      })}
    </div>
  );
};
