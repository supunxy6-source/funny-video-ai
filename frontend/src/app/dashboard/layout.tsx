'use client';

import React from 'react';
import { Sidebar } from '@/components/dashboard/Sidebar';
import { useAuth } from '@/hooks/useAuth';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { authed } = useAuth(true);

  if (authed === null) {
    return (
      <div className="min-h-screen bg-[#090d16] flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-sky-400"></div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[#090d16]">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-7xl mx-auto">
        {children}
      </main>
    </div>
  );
}
