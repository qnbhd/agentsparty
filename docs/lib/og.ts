/** The link-preview card, rendered by `scripts/generate-og.py`.
 *
 * Shared rather than declared in the root layout because a page that sets its
 * own `openGraph` replaces the layout's wholesale: without repeating the image
 * on every page, only the landing page would preview with one.
 *
 * The URL is relative on purpose — a leading slash resolves against the origin
 * of `metadataBase` and drops the basePath the docs are deployed under.
 */
export const ogImage = {
  url: 'og.png',
  width: 1200,
  height: 630,
  alt: 'agentsparty — protocol-first agents',
};
