import React from 'react';
import { Job } from '@/types';
import { Badge } from '@/components/ui/Badge';

export const PipelineStatus: React.FC<{ jobs: Job[] }> = ({ jobs }) => {
  const steps = [
    'discovery',
    'analysis',
    'scriptwriting',
    'visuals',
    'narration',
    'editing',
    'thumbnail',
    'seo',
    'upload',
    'notification',
  ];

  const getJobForStep = (stepName: string) => {
    return jobs.find((j) => j.step_name.toLowerCase() === stepName.toLowerCase());
  };

  return (
    <div className="py-2">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {steps.map((step, idx) => {
          const job = getJobForStep(step);
          const status = job ? job.status : 'pending';

          let variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' = 'neutral';
          if (status === 'completed') variant = 'success';
          else if (status === 'running') variant = 'info';
          else if (status === 'failed') variant = 'danger';

          return (
            <div
              key={step}
              className={`p-3 rounded-xl border flex flex-col items-center justify-center text-center transition-all ${
                status === 'running'
                  ? 'bg-sky-500/10 border-sky-500/40 shadow-lg shadow-sky-500/10'
                  : 'bg-slate-900/40 border-slate-800'
              }`}
            >
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1">
                Step {idx + 1}
              </span>
              <span className="text-xs font-semibold text-slate-200 capitalize mb-2">{step}</span>
              <Badge variant={variant} size="sm" pulse={status === 'running'}>
                {status}
              </Badge>
            </div>
          );
        })}
      </div>
    </div>
  );
};
