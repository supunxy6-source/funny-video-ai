'use client';

import React, { useState } from 'react';
import { Header } from '@/components/dashboard/Header';
import { Card } from '@/components/ui/Card';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useApi } from '@/hooks/useApi';
import { NewsArticle } from '@/types';

export default function ArticlesPage() {
  const [page, setPage] = useState(1);
  const { data } = useApi<{ items: NewsArticle[]; total: number }>(`/articles?page=${page}&page_size=15`);

  const columns = [
    {
      header: 'Headline',
      accessor: (a: NewsArticle) => (
        <div>
          <a
            href={a.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-slate-100 hover:text-sky-400 transition line-clamp-1"
          >
            {a.headline}
          </a>
          {a.summary && <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">{a.summary}</p>}
        </div>
      ),
    },
    {
      header: 'Category',
      accessor: (a: NewsArticle) => <Badge variant="info">{a.category}</Badge>,
    },
    {
      header: 'Verified',
      accessor: (a: NewsArticle) => (
        <Badge variant={a.is_verified ? 'success' : 'neutral'}>
          {a.is_verified ? 'Verified (3+ Sources)' : 'Unverified'}
        </Badge>
      ),
    },
    {
      header: 'Published',
      accessor: (a: NewsArticle) => (a.published_at ? new Date(a.published_at).toLocaleTimeString() : '-'),
    },
  ];

  return (
    <div>
      <Header
        title="Discovered News Articles"
        subtitle="Articles collected hourly from Reuters, AP, BBC, CNN, Al Jazeera, TechCrunch, and more"
      />

      <Card>
        <Table columns={columns} data={data?.items || []} emptyMessage="No news articles discovered yet" />

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
