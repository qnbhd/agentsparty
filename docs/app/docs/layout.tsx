import type { ReactNode } from 'react';
import { GlassLayout } from 'fumadocs-ui/layouts/glass';
import { baseOptions } from '@/app/layout.config';
import { pageTree } from '@/lib/source';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <GlassLayout tree={pageTree} {...baseOptions}>
      {children}
    </GlassLayout>
  );
}
