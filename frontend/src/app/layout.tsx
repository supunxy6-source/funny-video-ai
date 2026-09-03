import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Stateside Smiles — AI Comedy Video Platform',
  description: 'Fully autonomous AI entertainment platform that discovers trending memes, writes comedy scripts, edits videos, and publishes to YouTube daily.',
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
