'use client';

import React from 'react';
import { Header } from '@/components/dashboard/Header';
import { KPICard } from '@/components/dashboard/KPICard';
import { Card } from '@/components/ui/Card';
import { LineChart } from '@/components/charts/LineChart';
import { BarChart } from '@/components/charts/BarChart';
import { useApi } from '@/hooks/useApi';
import { AnalyticsOverview } from '@/types';

export default function AnalyticsPage() {
  const { data: analytics } = useApi<AnalyticsOverview>('/analytics/overview');

  const viewsData = [
    { label: 'Mon', value: 1200 },
    { label: 'Tue', value: 2400 },
    { label: 'Wed', value: 3100 },
    { label: 'Thu', value: 2800 },
    { label: 'Fri', value: 4500 },
    { label: 'Sat', value: 5200 },
    { label: 'Sun', value: 6100 },
  ];

  const categoryData = [
    { label: 'Politics', value: 45 },
    { label: 'Tech', value: 30 },
    { label: 'World', value: 25 },
    { label: 'Business', value: 20 },
    { label: 'Science', value: 15 },
  ];

  return (
    <div>
      <Header
        title="YouTube Channel Analytics"
        subtitle="Performance metrics, subscriber growth, and revenue estimations"
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard title="Total Views" value={analytics?.total_views || '12,450'} change="+24%" trend="up" icon="👁️" />
        <KPICard title="Subscribers" value={analytics?.total_subscribers || '1,820'} change="+12" trend="up" icon="👥" />
        <KPICard title="Estimated Revenue" value={`$${analytics?.estimated_revenue || '142.50'}`} change="Monthly" trend="up" icon="💰" />
        <KPICard title="Avg View Duration" value={`${analytics?.avg_view_duration || '6.4'} min`} change="78% retention" trend="up" icon="⏱️" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Weekly Views Growth" subtitle="Daily aggregated view count">
          <div className="pt-4">
            <LineChart data={viewsData} height={220} />
          </div>
        </Card>

        <Card title="Content Performance by Category" subtitle="Video distribution by news genre">
          <div className="pt-4">
            <BarChart data={categoryData} height={220} />
          </div>
        </Card>
      </div>
    </div>
  );
}
