'use client';

import React from 'react';
import Link from 'next/link';
import { Header } from '@/components/dashboard/Header';
import { VideoPreview } from '@/components/dashboard/VideoPreview';
import { useApi } from '@/hooks/useApi';
import { Video } from '@/types';

export default function VideosPage() {
  const { data } = useApi<{ items: Video[] }>('/videos?page_size=20');

  return (
    <div>
      <Header
        title="Generated Video Library"
        subtitle="Browse all rendered news videos with AI visuals, voice narration, and subtitle burn-in"
      />

      {data?.items && data.items.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.items.map((video) => (
            <Link key={video.id} href={`/dashboard/videos/${video.id}`}>
              <VideoPreview video={video} />
            </Link>
          ))}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-12 text-center text-slate-500">
          <span className="text-4xl block mb-2">🎬</span>
          <p className="text-sm font-medium">No videos generated yet</p>
          <p className="text-xs text-slate-600 mt-1">
            Trigger a pipeline run to generate your first AI news video.
          </p>
        </div>
      )}
    </div>
  );
}
