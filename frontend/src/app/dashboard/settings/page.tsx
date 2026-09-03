'use client';

import React, { useState, useEffect } from 'react';
import { Header } from '@/components/dashboard/Header';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { useApi } from '@/hooks/useApi';
import { fetchApi } from '@/lib/api';
import { Settings } from '@/types';

export default function SettingsPage() {
  const { data: settings, refetch } = useApi<Settings>('/settings');
  const [formState, setFormState] = useState<{
    provider?: string;
    dailyCount?: number;
    hour?: number;
    scheduleHours?: string;
    voiceId?: string;
    edgeVoice?: string;
    videoFormat?: string;
    youtubeAutoPublish?: boolean;
    youtubeDefaultPrivacy?: string;
  }>({});
  const [saving, setSaving] = useState(false);

  // Derive active values from local form state or fetched settings
  const provider = formState.provider ?? settings?.llm_primary_provider ?? 'google';
  const dailyCount = formState.dailyCount ?? settings?.daily_video_count ?? 3;
  const hour = formState.hour ?? settings?.pipeline_schedule_hour ?? 8;
  const scheduleHours = formState.scheduleHours ?? settings?.pipeline_schedule_hours ?? '8,12,16,20';
  const voiceId = formState.voiceId ?? settings?.elevenlabs_voice_id ?? '21m00Tcm4TlvDq8ikWAM';
  const edgeVoice = formState.edgeVoice ?? settings?.edge_tts_voice ?? 'en-US-AriaNeural';
  const videoFormat = formState.videoFormat ?? settings?.video_format ?? 'shorts';
  const youtubeAutoPublish = formState.youtubeAutoPublish ?? settings?.youtube_auto_publish ?? true;
  const youtubeDefaultPrivacy = formState.youtubeDefaultPrivacy ?? settings?.youtube_default_privacy ?? 'public';

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await fetchApi('/settings', {
        method: 'PUT',
        body: JSON.stringify({
          llm_primary_provider: provider,
          daily_video_count: Number(dailyCount),
          pipeline_schedule_hour: Number(hour),
          pipeline_schedule_hours: scheduleHours,
          elevenlabs_voice_id: voiceId,
          edge_tts_voice: edgeVoice,
          video_format: videoFormat,
          youtube_auto_publish: youtubeAutoPublish,
          youtube_default_privacy: youtubeDefaultPrivacy,
        }),
      });
      alert('Settings updated successfully!');
      refetch();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      alert(`Update failed: ${msg}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Header
        title="System Settings"
        subtitle="Configure daily 3-5 video production targets, YouTube publishing, neural TTS voices, and AI models"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Settings Form */}
        <div className="lg:col-span-2">
          <Card>
            <form onSubmit={handleSave} className="space-y-6">
              {/* Daily Video Production Target */}
              <div className="p-4 rounded-xl bg-sky-950/30 border border-sky-800/40">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-semibold text-sky-200">
                    🎯 Daily Video Production Target
                  </label>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-500/20 text-sky-400 border border-sky-500/30">
                    {dailyCount} Videos / Day
                  </span>
                </div>
                <p className="text-xs text-slate-400 mb-3">
                  Set how many distinct news videos should be automatically produced and published daily.
                </p>
                <div className="grid grid-cols-4 gap-2">
                  {[1, 3, 4, 5].map((cnt) => (
                    <button
                      key={cnt}
                      type="button"
                      onClick={() => setFormState((prev) => ({ ...prev, dailyCount: cnt }))}
                      className={`py-2 px-3 rounded-lg text-xs font-semibold transition-all border ${
                        dailyCount === cnt
                          ? 'bg-sky-500 text-white border-sky-400 shadow-lg shadow-sky-500/20'
                          : 'bg-slate-900/80 text-slate-300 border-slate-700 hover:border-slate-500'
                      }`}
                    >
                      {cnt === 1 ? '1 Video (Single)' : `${cnt} Videos / Day`}
                    </button>
                  ))}
                </div>
              </div>

              {/* YouTube Publishing Options */}
              <div className="p-4 rounded-xl bg-red-950/20 border border-red-800/30 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-red-200 flex items-center gap-2">
                      <span>📺</span> YouTube Publishing
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Automatically upload rendered shorts and videos directly to your YouTube channel.
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={youtubeAutoPublish}
                      onChange={(e) => setFormState((prev) => ({ ...prev, youtubeAutoPublish: e.target.checked }))}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
                  </label>
                </div>

                {youtubeAutoPublish && (
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1.5">
                      Default Video Privacy Status
                    </label>
                    <select
                      value={youtubeDefaultPrivacy}
                      onChange={(e) => setFormState((prev) => ({ ...prev, youtubeDefaultPrivacy: e.target.value }))}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-red-500"
                    >
                      <option value="public">🌐 Public (Instantly visible to all YouTube viewers & Shorts feed)</option>
                      <option value="unlisted">🔗 Unlisted (Visible only to anyone with the video link)</option>
                      <option value="private">🔒 Private (Visible only to you for review before publishing)</option>
                    </select>
                  </div>
                )}
              </div>

              {/* LLM Provider */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Primary LLM Script Provider
                </label>
                <select
                  value={provider}
                  onChange={(e) => setFormState((prev) => ({ ...prev, provider: e.target.value }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                >
                  <option value="google">Google Gemini (Gemini 2.0 Flash) — Fast & Reliable</option>
                  <option value="openai">OpenAI (GPT-4o)</option>
                  <option value="anthropic">Anthropic (Claude Sonnet 4)</option>
                </select>
              </div>

              {/* Video Format */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Video Format & Aspect Ratio
                </label>
                <select
                  value={videoFormat}
                  onChange={(e) => setFormState((prev) => ({ ...prev, videoFormat: e.target.value }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                >
                  <option value="shorts">⚡ YouTube Shorts (Vertical 9:16 — 1080x1920, &lt;60s)</option>
                  <option value="landscape">Standard Broadcast (Horizontal 16:9 — 1920x1080)</option>
                </select>
              </div>

              {/* TTS Voice */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  TTS Voice (Neural Female News Anchor)
                </label>
                <select
                  value={edgeVoice}
                  onChange={(e) => setFormState((prev) => ({ ...prev, edgeVoice: e.target.value }))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                >
                  <option value="en-US-AriaNeural">👩 Aria Neural (US Female — Professional News Anchor)</option>
                  <option value="en-US-JennyNeural">👩 Jenny Neural (US Female — Expressive & Natural)</option>
                  <option value="en-US-AvaNeural">👩 Ava Neural (US Female — Crisp & Modern)</option>
                  <option value="en-GB-SoniaNeural">👩 Sonia Neural (UK Female — BBC / Broadcast Tone)</option>
                </select>
              </div>

              {/* Scheduling Hours */}
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Primary Schedule Hour (UTC)"
                  type="number"
                  min="0"
                  max="23"
                  value={hour}
                  onChange={(e) => setFormState((prev) => ({ ...prev, hour: Number(e.target.value) }))}
                />
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Daily Schedule Slots (Hours UTC)
                  </label>
                  <input
                    type="text"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                    value={scheduleHours}
                    onChange={(e) => setFormState((prev) => ({ ...prev, scheduleHours: e.target.value }))}
                    placeholder="e.g. 8,12,16,20"
                  />
                  <span className="text-[11px] text-slate-500 mt-1 block">Comma-separated UTC hours</span>
                </div>
              </div>

              {/* ElevenLabs Voice ID */}
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  ElevenLabs Female Voice ID (Optional)
                </label>
                <input
                  type="text"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                  value={voiceId}
                  onChange={(e) => setFormState((prev) => ({ ...prev, voiceId: e.target.value }))}
                  placeholder="e.g. 21m00Tcm4TlvDq8ikWAM (Rachel)"
                />
                <span className="text-[11px] text-slate-400 mt-1 block">
                  Default: <code>21m00Tcm4TlvDq8ikWAM</code> (Rachel) | Alternate: <code>EXAVITQu4vr4xnSDxMaL</code> (Sarah)
                </span>
              </div>

              <Button type="submit" loading={saving} size="md">
                Save All Settings
              </Button>
            </form>
          </Card>
        </div>

        {/* Channel & Status Sidebar Card */}
        <div className="space-y-6">
          <Card title="Connected YouTube Channel">
            {settings?.youtube_channel_info?.authenticated ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="w-12 h-12 rounded-full bg-red-600/20 text-red-500 flex items-center justify-center text-xl font-bold border border-red-500/30">
                    ▶️
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-100">
                      {settings.youtube_channel_info.title}
                    </h4>
                    <span className="text-[11px] text-emerald-400 font-medium flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      OAuth Connected & Active
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800/80">
                    <span className="text-slate-500 block">Subscribers</span>
                    <span className="text-slate-100 font-semibold">{settings.youtube_channel_info.subscriber_count ?? 0}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800/80">
                    <span className="text-slate-500 block">Total Videos</span>
                    <span className="text-slate-100 font-semibold">{settings.youtube_channel_info.video_count ?? 0}</span>
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 space-y-1">
                  <div>Channel ID: <code className="text-slate-300">{settings.youtube_channel_info.channel_id}</code></div>
                  <div>Default Privacy: <Badge variant="success">{youtubeDefaultPrivacy.toUpperCase()}</Badge></div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <div className="w-12 h-12 rounded-full bg-amber-500/10 text-amber-400 mx-auto flex items-center justify-center text-xl mb-2">
                  ⚠️
                </div>
                <p className="text-xs font-semibold text-slate-200">YouTube Channel Not Detected</p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Place OAuth credentials in <code>config/youtube_token.json</code> or run the auth setup.
                </p>
              </div>
            )}
          </Card>

          <Card title="Production Summary">
            <div className="space-y-3 text-xs text-slate-300">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Target Output:</span>
                <span className="font-semibold text-sky-400">{dailyCount} videos / day</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Auto YouTube Upload:</span>
                <span className="font-semibold">{youtubeAutoPublish ? '✅ Enabled' : '⏸️ Manual Only'}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Format:</span>
                <span className="font-semibold text-slate-200">9:16 Shorts (1080x1920)</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Audio Voice:</span>
                <span className="font-semibold text-slate-200">Neural Female News Voice</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
