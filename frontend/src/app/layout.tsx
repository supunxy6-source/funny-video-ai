import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AI News Studio — Autonomous AI Video Platform',
  description: 'Fully autonomous AI News Video platform that discovers, writes, edits, and publishes news videos to YouTube daily.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#090d16] text-slate-100 min-h-screen antialiased selection:bg-sky-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
