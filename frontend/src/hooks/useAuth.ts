'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { isAuthenticated, clearTokens } from '@/lib/auth';

export function useAuth(requireAuth = true) {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const router = useRouter();

  useEffect(() => {
    const check = isAuthenticated();
    setAuthed(check);
    if (requireAuth && !check) {
      router.push('/login');
    }
  }, [requireAuth, router]);

  const logout = () => {
    clearTokens();
    setAuthed(false);
    router.push('/login');
  };

  return { authed, logout };
}
