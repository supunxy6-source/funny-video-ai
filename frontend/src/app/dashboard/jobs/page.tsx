'use client';

import React, { useState } from 'react';
import { Header } from '@/components/dashboard/Header';
import { Card } from '@/components/ui/Card';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useApi } from '@/hooks/useApi';
import { usePolling } from '@/hooks/usePolling';
import { Job } from '@/types';

export default function JobsPage() {
  const [page, setPage] = useState(1);
  const { data, refetch } = useApi<{ items: Job[]; total: number }>(`/jobs?page=${page}&page_size=15`);

  usePolling(() => refetch(), 5000);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>;
      case 'running':
        return <Badge variant="info" pulse>Running</Badge>;
      case 'failed':
        return <Badge variant="danger">Failed</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const columns = [
    {
      header: 'Step',
      accessor: (j: Job) => (
        <span className="font-semibold text-slate-100 capitalize">{j.step_name}</span>
      ),
    },
    {
      header: 'Run ID',
      accessor: (j: Job) => <code className="text-xs text-sky-400 font-mono">{j.pipeline_run_id}</code>,
    },
    {
      header: 'Status',
      accessor: (j: Job) => getStatusBadge(j.status),
    },
    {
      header: 'Duration',
      accessor: (j: Job) => (j.duration_seconds ? `${j.duration_seconds.toFixed(1)}s` : '-'),
    },
    {
      header: 'Started At',
      accessor: (j: Job) => (j.started_at ? new Date(j.started_at).toLocaleString() : '-'),
    },
    {
      header: 'Retries',
      accessor: (j: Job) => `${j.retry_count}`,
    },
  ];

  return (
    <div>
      <Header
        title="Pipeline Jobs Monitor"
        subtitle="Track background execution of each autonomous pipeline step"
      />

      <Card>
        <Table columns={columns} data={data?.items || []} emptyMessage="No pipeline jobs recorded yet" />

        <div className="flex justify-between items-center mt-4 text-xs text-slate-400">
          <span>Showing page {page}</span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="secondary"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(p - 1, 1))}
            >
              Previous
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={!data || data.items.length < 15}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
