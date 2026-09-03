export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface NewsArticle {
  id: number;
  source_id: number;
  headline: string;
  summary?: string;
  body?: string;
  url: string;
  image_url?: string;
  author?: string;
  published_at?: string;
  category: string;
  cluster_id?: number;
  credibility_score: number;
  is_verified: boolean;
  created_at: string;
}

export interface ScriptScene {
  order: number;
  scene_type: string;
  title: string;
  text: string;
  visual_prompt?: string;
  visual_type?: string;
}

export interface Script {
  id: number;
  title: string;
  topic_summary: string;
  content: string;
  content_json?: string;
  article_ids: string;
  word_count: number;
  duration_estimate: number;
  llm_provider: string;
  llm_model: string;
  status: 'draft' | 'approved' | 'used' | 'rejected';
  created_at: string;
}

export interface Video {
  id: number;
  script_id: number;
  file_path: string;
  subtitle_path?: string;
  duration: number;
  resolution: string;
  fps: number;
  file_size: number;
  codec: string;
  status: 'rendering' | 'ready' | 'uploaded' | 'failed';
  youtube_video_id?: string;
  upload_status?: string;
  created_at: string;
}

export interface Settings {
  llm_primary_provider: string;
  daily_video_count: number;
  pipeline_schedule_hour: number;
  pipeline_schedule_minute: number;
  pipeline_schedule_hours: string;
  pipeline_timezone: string;
  news_discovery_interval_minutes: number;
  elevenlabs_voice_id: string;
  edge_tts_voice: string;
  video_format: string;
  youtube_category_id: string;
  youtube_playlist_id: string;
  youtube_auto_publish: boolean;
  youtube_default_privacy: string;
  youtube_channel_info?: {
    authenticated: boolean;
    channel_id?: string;
    title?: string;
    custom_url?: string;
    subscriber_count?: number;
    view_count?: number;
    video_count?: number;
    thumbnail_url?: string;
    error?: string;
  };
}

export interface Job {
  id: number;
  pipeline_run_id: string;
  step_name: string;
  step_order: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'retrying';
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  error_message?: string;
  retry_count: number;
  created_at: string;
}

export interface Upload {
  id: number;
  video_id: number;
  youtube_video_id?: string;
  title: string;
  description: string;
  tags: string;
  privacy_status: string;
  status: 'pending' | 'uploading' | 'processing' | 'published' | 'failed';
  scheduled_at?: string;
  published_at?: string;
  created_at: string;
}

export interface Log {
  id: number;
  job_id?: number;
  pipeline_run_id?: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  message: string;
  module?: string;
  timestamp: string;
}

export interface DashboardStats {
  total_videos: number;
  total_articles: number;
  videos_today: number;
  articles_today: number;
  active_jobs: number;
  total_uploads: number;
  success_rate: number;
  last_pipeline_run?: string;
}

export interface AnalyticsOverview {
  total_views: number;
  total_subscribers: number;
  estimated_revenue: number;
  avg_view_duration: number;
  videos_this_week: number;
  views_this_week: number;
}
