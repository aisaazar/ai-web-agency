import type { MetadataRoute } from "next";

import { buildSitemap } from "@/lib/manifests";

/** Static: generated at build time from the content artifact, never at request time. */
export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return buildSitemap();
}
