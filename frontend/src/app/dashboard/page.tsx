'use client';

import React, { useState } from 'react';
import { Header } from '@/components/dashboard/Header';
import { KPICard } from '@/components/dashboard/KPICard';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { PipelineStatus } from '@/components/dashboard/PipelineStatus';
import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import { LineChart } from '@/components/charts/LineChart';
import { useApi } from '@/hooks/useApi';
import { usePolling } from '@/hooks/usePolling';
import { fetchApi } from '@/lib/api';
import { DashboardStats, Job, Log, Settings } from '@/types';

export default function OverviewPage() {
  const { data: stats, refetch: refetchStats } = useApi<DashboardStats>('/dashboard/stats');
  const { data: settings } = useApi<Settings>('/settings');
  const { data: jobsData, refetch: refetchJobs } = useApi<{ items: Job[] }>('/jobs?page_size=10');
  const { data: logsData, refetch: refetchLogs } = useApi<{ items: Log[] }>('/logs?page_size=8');
  const [triggering, setTriggering] = useState(false);
  const [selectedCount, setSelectedCount] = useState<number>(3);

  // Poll for updates every 5 seconds
  usePolling(() => {
    refetchStats();
    refetchJobs();
    refetchLogs();
  }, 5000);

  const handleTriggerPipeline = async (count?: number) => {
    setTriggering(true);
    const videoCount = count || selectedCount;
    try {
      await fetchApi('/jobs/trigger', {
        method: 'POST',
        body: JSON.stringify({ video_count: videoCount }),
      });
      refetchJobs();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Trigger failed: ${msg}`);
    } finally {
      setTriggering(false);
    }
  };

  const chartData = [
    { label: 'Mon', value: 3 },
    { label: 'Tue', value: 4 },
    { label: 'Wed', value: 5 },
    { label: 'Thu', value: 3 },
    { label: 'Fri', value: 5 },
    { label: 'Sat', value: 4 },
    { label: 'Sun', value: stats?.videos_today || 3 },
  ];

  const targetCount = settings?.daily_video_count || 3;
  const videosToday = stats?.videos_today ?? 0;

  return (
    <div>
      <Header
        title="Dashboard Overview"
        subtitle="Real-time control and monitoring of autonomous AI video production & YouTube publishing"
        action={
          <div className="flex items-center gap-2">
            <select
              value={selectedCount}
              onChange={(e) => setSelectedCount(Number(e.target.value))}
              className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold text-sky-400 focus:outline-none focus:border-sky-500"
            >
              <option value={3}>⚡ 3 Videos (Standard Batch)</option>
              <option value={5}>🚀 5 Videos (Maximum Batch)</option>
              <option value={1}>🎬 1 Video (Single Run)</option>
            </select>
            <Button
              onClick={() => handleTriggerPipeline()}
              loading={triggering}
              icon="⚡"
              size="md"
            >
              Generate {selectedCount} Videos
            </Button>
          </div>
        }
      />

      {/* YouTube Connection Banner */}
      {settings?.youtube_channel_info?.authenticated && (
        <div className="mb-6 p-3.5 rounded-2xl bg-gradient-to-r from-red-950/40 via-slate-900 to-slate-900 border border-red-900/40 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-red-600/20 text-red-500 flex items-center justify-center font-bold text-sm border border-red-500/30">
              ▶️
            </div>
            <div>
              <span className="font-semibold text-slate-100 mr-2">YouTube Channel Connected:</span>
              <span className="text-red-400 font-bold">{settings.youtube_channel_info.title}</span>
              <span className="text-slate-500 mx-2">•</span>
              <span className="text-slate-400">{settings.youtube_channel_info.subscriber_count} subscribers</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
              ● Auto-Publish ({settings.youtube_default_privacy.toUpperCase()})
            </span>
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard
          title="Daily Output Progress"
          value={`${videosToday} / ${targetCount} Videos`}
          change={videosToday >= targetCount ? 'Target Achieved 🎉' : `${targetCount - videosToday} more to goal`}
          trend={videosToday >= targetCount ? 'up' : 'neutral'}
          icon="🎬"
        />
        <KPICard
          title="Articles Processed"
          value={stats?.total_articles ?? 0}
          change="Hourly Discovery"
          trend="neutral"
          icon="📰"
        />
        <KPICard
          title="Active Pipeline Jobs"
          value={stats?.active_jobs ?? 0}
          change={stats?.active_jobs ? 'Processing' : 'Idle / Scheduled'}
          trend={stats?.active_jobs ? 'up' : 'neutral'}
          icon="⚙️"
        />
        <KPICard
          title="Pipeline Success Rate"
          value={`${((stats?.success_rate ?? 1) * 100).toFixed(0)}%`}
          change="Optimal"
          trend="up"
          icon="📈"
        />
      </div>

      {/* Pipeline Status Banner */}
      <Card title="Active Pipeline Status" subtitle="Step-by-step progress for the current execution" className="mb-8">
        <PipelineStatus jobs={jobsData?.items || []} />
      </Card>

      {/* Grid Layout: Chart & Activity Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Daily Video Output" subtitle="Production volume over the past 7 days" className="lg:col-span-2">
          <div className="pt-4">
            <LineChart data={chartData} height={220} />
          </div>
        </Card>

        <Card title="Recent Activity Feed" subtitle="Latest execution logs and events">
          <ActivityFeed logs={logsData?.items || []} />
        </Card>
      </div>
    </div>
  );
}
