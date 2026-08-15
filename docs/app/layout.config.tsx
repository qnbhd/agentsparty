import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
import Image from 'next/image';
import logo from '@/public/logo.svg';

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: (
      <>
        <Image src={logo} alt="" width={22} height={22} aria-hidden />
        <span className="font-medium">agentsparty</span>
        <span className="font-mono text-xs text-fd-muted-foreground">0.1.x</span>
      </>
    ),
  },
  githubUrl: 'https://github.com/qnbhd/agentsparty',
};
