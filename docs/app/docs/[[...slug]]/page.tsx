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
import { getMDXComponents } from '@/mdx-components';
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
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      {/* page actions: copy Markdown or open it in an AI tool */}
      <div className="flex flex-row items-center gap-2 border-b pt-2 pb-6">
        <MarkdownCopyButton markdownUrl={markdownUrl} />
        <ViewOptionsPopover markdownUrl={markdownUrl} />
      </div>
      <DocsBody>
        <MDX components={getMDXComponents()} />
      </DocsBody>
    </DocsPage>
  );
}

export function generateStaticParams() {
  return source.generateParams();
}
