'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { Header } from '@/components/dashboard/Header';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useApi } from '@/hooks/useApi';
import { fetchApi } from '@/lib/api';
import { Video, Script } from '@/types';

export default function VideoDetailPage() {
  const params = useParams();
  const videoId = params.id as string;

  const { data: video, refetch: refetchVideo } = useApi<Video>(`/videos/${videoId}`);
  const { data: script, refetch: refetchScript } = useApi<Script>(
    video ? `/scripts/${video.script_id}` : ''
  );

  const [editingContent, setEditingContent] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [privacyChoice, setPrivacyChoice] = useState('public');

  const isYouTubePublished = video?.youtube_video_id && !video.youtube_video_id.startsWith('local_');

  const handleSaveScript = async () => {
    if (!script || editingContent === null) return;
    setSaving(true);
    try {
      await fetchApi(`/scripts/${script.id}`, {
        method: 'PUT',
        body: JSON.stringify({ content: editingContent }),
      });
      refetchScript();
      setEditingContent(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Save failed: ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  const handleTriggerUpload = async () => {
    setPublishing(true);
    try {
      await fetchApi(`/uploads`, {
        method: 'POST',
        body: JSON.stringify({ video_id: Number(videoId), privacy_status: privacyChoice }),
      });
      alert(`Upload to YouTube triggered as ${privacyChoice.toUpperCase()}!`);
      setTimeout(() => refetchVideo(), 2000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Publish failed: ${msg}`);
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div>
      <Header
        title={`Video #${videoId}`}
        subtitle="Preview video, edit generated script, inspect metadata, or publish to YouTube"
        action={
          <div className="flex items-center gap-2">
            {isYouTubePublished ? (
              <a
                href={`https://youtube.com/watch?v=${video.youtube_video_id}`}
                target="_blank"
                rel="noreferrer"
                className="py-2 px-4 rounded-xl text-xs font-bold bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/30 transition-all flex items-center gap-1.5"
              >
                <span>▶</span> Watch on YouTube
              </a>
            ) : (
              <div className="flex items-center gap-2">
                <select
                  value={privacyChoice}
                  onChange={(e) => setPrivacyChoice(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 focus:outline-none focus:border-red-500"
                >
                  <option value="public">Public</option>
                  <option value="unlisted">Unlisted</option>
                  <option value="private">Private</option>
                </select>
                <Button onClick={handleTriggerUpload} loading={publishing} icon="🚀" size="md">
                  Publish to YouTube
                </Button>
              </div>
            )}
          </div>
        }
      />

      {isYouTubePublished && (
        <div className="mb-6 p-4 rounded-2xl bg-red-950/30 border border-red-800/40 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl text-red-500">▶️</span>
            <div>
              <h4 className="text-sm font-semibold text-white">Live on YouTube</h4>
              <p className="text-xs text-slate-400">Video ID: <code className="text-red-300">{video.youtube_video_id}</code></p>
            </div>
          </div>
          <a
            href={`https://youtube.com/watch?v=${video.youtube_video_id}`}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-red-400 hover:text-red-300 font-semibold underline"
          >
            Open in YouTube ↗
          </a>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Video Player Card */}
        <Card title="Video Preview (YouTube Shorts)" className="lg:col-span-2">
          <div className="max-w-xs mx-auto aspect-[9/16] bg-black rounded-2xl overflow-hidden flex flex-col items-center justify-center border border-slate-800 shadow-2xl relative">
            <span className="text-6xl text-sky-400/50 mb-3">▶️</span>
            <span className="px-3 py-1 rounded-full text-xs font-bold tracking-wider bg-red-600/90 text-white shadow-lg">
              ⚡ YOUTUBE SHORTS
            </span>
          </div>

          <div className="flex items-center justify-between mt-4 text-xs text-slate-400">
            <span>Status: <Badge variant="success">{video?.status || 'ready'}</Badge></span>
            <span>Duration: {video?.duration ? (video.duration < 60 ? `${Math.round(video.duration)}s` : `${(video.duration / 60).toFixed(1)} mins`) : '0s'}</span>
            <span className="font-mono text-sky-400">Resolution: {video?.resolution || '1080x1920'}</span>
            <span>Size: {((video?.file_size || 0) / (1024 * 1024)).toFixed(1)} MB</span>
          </div>
        </Card>

        {/* Details & Metadata Card */}
        <Card title="Metadata & Specs">
          <div className="space-y-4 text-xs">
            <div>
              <span className="text-slate-500 uppercase tracking-wider block mb-1">LLM Model</span>
              <span className="text-slate-200 font-medium">{script?.llm_provider} / {script?.llm_model}</span>
            </div>
            <div>
              <span className="text-slate-500 uppercase tracking-wider block mb-1">Word Count</span>
              <span className="text-slate-200 font-medium">{script?.word_count} words</span>
            </div>
            <div>
              <span className="text-slate-500 uppercase tracking-wider block mb-1">Audio Codec</span>
              <span className="text-slate-200 font-medium">{video?.codec || 'h264 / aac'}</span>
            </div>
            <div>
              <span className="text-slate-500 uppercase tracking-wider block mb-1">Subtitles</span>
              <span className="text-slate-200 font-medium">{video?.subtitle_path ? 'Generated (SRT)' : 'None'}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Script Editor Card */}
      <Card
        title="Generated Script"
        subtitle="Review and edit the factual script generated by the LLM"
        action={
          editingContent !== null ? (
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" onClick={() => setEditingContent(null)}>
                Cancel
              </Button>
              <Button size="sm" loading={saving} onClick={handleSaveScript}>
                Save Script
              </Button>
            </div>
          ) : (
            <Button size="sm" variant="outline" onClick={() => setEditingContent(script?.content || '')}>
              Edit Script
            </Button>
          )
        }
      >
        {editingContent !== null ? (
          <textarea
            className="w-full h-96 bg-slate-950 border border-slate-700 rounded-xl p-4 text-sm font-mono text-slate-200 focus:outline-none focus:border-sky-500"
            value={editingContent}
            onChange={(e) => setEditingContent(e.target.value)}
          />
        ) : (
          <div className="prose prose-invert max-w-none text-sm text-slate-300 whitespace-pre-wrap font-sans leading-relaxed bg-slate-950/60 p-5 rounded-xl border border-slate-800">
            {script?.content || 'Loading script...'}
          </div>
        )}
      </Card>
    </div>
  );
}
