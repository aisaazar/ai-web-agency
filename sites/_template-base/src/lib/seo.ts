/**
 * Deterministic SEO metadata. Meta, canonical, hreflang and robots directives are derived from the
 * content artifact (`seo.pages`) — never hand-written per page and never produced by a model
 * (docs/AI-AND-PROVIDERS.md section 1).
 */
import type { Metadata } from "next";

import { absoluteUrl, content, pageSeo } from "./content";

export function buildPageMetadata(pathname: string): Metadata {
  const page = pageSeo(pathname);
  const url = absoluteUrl(pathname);

  return {
    title: page.title,
    description: page.description,
    alternates: {
      canonical: url,
      // A self-referencing hreflang is the honest signal while there is exactly one locale; adding
      // a second locale means adding a second content artifact, not inventing an alternate here.
      languages: {
        [content.locale]: url,
        "x-default": url,
      },
    },
    robots: page.noindex
      ? { index: false, follow: false }
      : { index: true, follow: true },
    openGraph: {
      type: "website",
      url,
      title: page.title,
      description: page.description,
      siteName: content.site.name,
      locale: content.locale,
      ...(content.site.og_image
        ? {
            images: [
              {
                url: content.site.og_image,
                alt: content.compliance.og_image_alt ?? content.site.name,
              },
            ],
          }
        : {}),
    },
    twitter: { card: "summary" },
  };
}
