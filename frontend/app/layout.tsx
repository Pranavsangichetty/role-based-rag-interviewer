import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Role-Based RAG Interviewer',
  description: 'AI-powered technical interviewer grounded in role-specific knowledge bases and candidate resume signals.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
