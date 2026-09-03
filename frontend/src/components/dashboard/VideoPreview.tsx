import React from 'react';
import { Video } from '@/types';
import { Badge } from '@/components/ui/Badge';

export const VideoPreview: React.FC<{ video: Video }> = ({ video }) => {
  const isShorts = video.resolution?.includes('1080x1920') || video.duration < 90;
  const isYouTubePublished = video.youtube_video_id && !video.youtube_video_id.startsWith('local_');

  return (
    <div className="glass-card rounded-2xl overflow-hidden border border-slate-800 group hover:border-sky-500/50 transition-all flex flex-col justify-between">
      <div>
        <div className={`relative ${isShorts ? 'aspect-[9/14] max-h-72' : 'aspect-video'} bg-slate-950 flex items-center justify-center border-b border-slate-800`}>
          <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/20 to-transparent z-10"></div>
          <div className="text-center z-20">
            <span className="text-4xl text-sky-400/80 group-hover:scale-110 transition-transform block">🎬</span>
            <div className="flex items-center justify-center gap-1.5 mt-2">
              {isShorts && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider bg-red-600/80 text-white shadow-lg">
                  ⚡ SHORTS
                </span>
              )}
              {isYouTubePublished && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider bg-red-500 text-white shadow-lg flex items-center gap-1">
                  <span>▶</span> YOUTUBE
                </span>
              )}
            </div>
          </div>
          <div className="absolute bottom-3 left-3 right-3 z-20 flex justify-between items-center">
            <Badge variant={video.status === 'uploaded' ? 'success' : video.status === 'ready' ? 'success' : 'warning'}>
              {video.status === 'uploaded' ? 'published' : video.status}
            </Badge>
            <span className="text-xs font-mono text-slate-300 bg-black/70 px-2 py-0.5 rounded backdrop-blur">
              {video.duration < 60 ? `${Math.round(video.duration)}s` : `${(video.duration / 60).toFixed(1)} mins`}
            </span>
          </div>
        </div>
        <div className="p-4">
          <h4 className="text-sm font-semibold text-slate-100 line-clamp-1">
            {isShorts ? `YouTube Short #${video.id}` : `Rendered Video #${video.id}`}
          </h4>
          <div className="flex items-center justify-between text-xs text-slate-400 mt-2">
            <span className="font-mono text-sky-400/80">{video.resolution || '1080x1920'}</span>
            <span>{((video.file_size || 0) / (1024 * 1024)).toFixed(1)} MB</span>
            <span className="capitalize">{video.codec || 'h264'}</span>
          </div>
        </div>
      </div>

      {isYouTubePublished && (
        <div className="px-4 pb-3 pt-0">
          <a
            href={`https://youtube.com/watch?v=${video.youtube_video_id}`}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="w-full py-1.5 px-3 rounded-lg text-xs font-medium bg-red-600/10 text-red-400 hover:bg-red-600 hover:text-white border border-red-500/20 transition-all flex items-center justify-center gap-1.5"
          >
            <span>▶</span> Watch on YouTube
          </a>
        </div>
      )}
    </div>
  );
};
