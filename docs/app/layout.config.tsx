import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
import Image from 'next/image';
import logo from '@/public/logo.svg';

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: (
      <>
        <Image src={logo} alt="" width={20} height={20} aria-hidden />
        agentsparty
      </>
    ),
  },
  githubUrl: 'https://github.com/qnbhd/agentsparty',
};
