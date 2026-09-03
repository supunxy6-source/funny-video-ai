'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const { logout } = useAuth(false);

  const navItems = [
    { label: 'Overview', href: '/dashboard', icon: '📊' },
    { label: 'Pipeline Jobs', href: '/dashboard/jobs', icon: '⚙️' },
    { label: 'Trending Content', href: '/dashboard/articles', icon: '😂' },
    { label: 'Generated Videos', href: '/dashboard/videos', icon: '🎬' },
    { label: 'Analytics', href: '/dashboard/analytics', icon: '📈' },
    { label: 'System Logs', href: '/dashboard/logs', icon: '📜' },
    { label: 'Settings', href: '/dashboard/settings', icon: '⚙️' },
  ];

  return (
    <aside className="w-64 glass-panel h-screen flex flex-col justify-between p-4 sticky top-0 z-30 border-r border-slate-800">
      <div>
        <div className="flex items-center gap-3 px-3 py-4 mb-6 border-b border-slate-800/80">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-amber-500 to-pink-600 flex items-center justify-center font-bold text-white shadow-lg shadow-amber-500/30">
            😄
          </div>
          <div>
            <h1 className="font-bold text-slate-100 text-sm tracking-wide glow-blue">STATESIDE SMILES</h1>
            <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">COMEDY AI</span>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-sky-500/20 to-indigo-500/10 text-sky-400 border border-sky-500/30 shadow-md shadow-sky-500/5'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <span className="text-base">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="pt-4 border-t border-slate-800/80">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-sm font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all cursor-pointer"
        >
          <span>🚪</span>
          Logout
        </button>
      </div>
    </aside>
  );
};
