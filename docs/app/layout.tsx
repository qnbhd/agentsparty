import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { RootProvider } from 'fumadocs-ui/provider/next';
import { ogImage } from '@/lib/og';
import './global.css';

const siteName = 'agentsparty';
const siteDescription =
  'Declarative multiparty session protocols for AI agents.';
// Absolute URLs for canonical and og:* tags. The docs ship as a static export
// under a basePath, so the origin cannot be inferred at request time.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://qnbhd.github.io';
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

export const metadata: Metadata = {
  metadataBase: new URL(`${siteUrl}${basePath}/`),
  title: {
    default: 'agentsparty — protocol-first agents',
    template: '%s | agentsparty',
  },
  description: siteDescription,
  applicationName: siteName,
  openGraph: {
    type: 'website',
    siteName,
    title: 'agentsparty — protocol-first agents',
    description: siteDescription,
    images: [ogImage],
  },
  twitter: {
    // The only card variant that renders the image at a legible size.
    card: 'summary_large_image',
    title: 'agentsparty — protocol-first agents',
    description: siteDescription,
    images: [ogImage],
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    /* `next-themes` writes `class` and `color-scheme` on <html> after hydration,
     * so the server markup carries neither and the mismatch is expected. The
     * landing hero opts out of the theme entirely — it paints its own palette. */
    <html lang="en" suppressHydrationWarning>
      <body>
        <RootProvider search={{ options: { type: 'static' } }}>
          {children}
        </RootProvider>
      </body>
    </html>
  );
}
