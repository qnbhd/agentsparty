import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  // Emits `<route>/index.html` instead of `<route>.html`, which every static
  // host resolves without extension rewriting, and makes the relative links in
  // authored MDX resolve against the page's own directory.
  trailingSlash: true,
  basePath,
  assetPrefix: basePath ? `${basePath}/` : undefined,
  images: { unoptimized: true },
  turbopack: { root: process.cwd() },
};

export default withMDX(nextConfig);
