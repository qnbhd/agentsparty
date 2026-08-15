import type { ReactNode } from 'react';
import { RootProvider } from 'fumadocs-ui/provider/next';
import './global.css';

export const metadata = {
  title: {
    default: 'agentsparty — protocol-first agents',
    template: '%s | agentsparty',
  },
  description: 'Declarative multiparty session types for AI agents.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <RootProvider search={{ options: { type: 'static' } }}>{children}</RootProvider>
      </body>
    </html>
  );
}
