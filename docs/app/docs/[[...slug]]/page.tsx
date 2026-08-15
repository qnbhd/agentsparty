import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
} from 'fumadocs-ui/layouts/glass/page';
import {
  MarkdownCopyButton,
  ViewOptionsPopover,
} from '@/components/ai/page-actions';
import { PageStatusBadge } from '@/components/page-status';
import { getMDXComponents } from '@/mdx-components';
import { ogImage } from '@/lib/og';
import { source } from '@/lib/source';

export default async function Page({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const page = source.getPage((await params).slug);
  if (!page) notFound();

  const MDX = page.data.body;
  // expose the statically generated Markdown representation to agents:
  const markdownUrl = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}${page.url}.md`;
  return (
    <DocsPage toc={page.data.toc} full={page.data.full}>
      {/* Title row: the copy/open actions share the title's line so a page
       * opens on its heading, not on a band of controls floating above it. */}
      <div className="flex flex-row items-center justify-between gap-3">
        <DocsTitle className="ap-docs-title">{page.data.title}</DocsTitle>
        <span className="flex shrink-0 flex-row items-center gap-2">
          <MarkdownCopyButton markdownUrl={markdownUrl} />
          <ViewOptionsPopover markdownUrl={markdownUrl} />
        </span>
      </div>
      <DocsDescription className="ap-docs-description">{page.data.description}</DocsDescription>
      <DocsBody>
        <MDX components={getMDXComponents()} />
      </DocsBody>
      {/* Foot: the page status lands after the prose. */}
      {page.data.status ? (
        <div className="flex flex-row flex-wrap items-center gap-2 pt-4 mb-6">
          <PageStatusBadge status={page.data.status} />
        </div>
      ) : null}
    </DocsPage>
  );
}

// Without this every page would inherit the root title and description, so
// tabs, bookmarks, search results, and link previews would all read alike.
export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}): Promise<Metadata> {
  const page = source.getPage((await params).slug);
  if (!page) notFound();

  const { title, description } = page.data;
  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url: page.url,
      type: 'article',
      images: [ogImage],
    },
    twitter: { title, description, images: [ogImage] },
    alternates: { canonical: page.url },
  };
}

export function generateStaticParams() {
  return source.generateParams();
}
