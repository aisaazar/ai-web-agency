import type { MetadataRoute } from "next";

import { buildRobots } from "@/lib/manifests";

/**
 * robots.txt: everything may be crawled, explicitly including the AI answer-engine crawlers. AEO
 * (the "A" in the product name) is impossible if the site blocks the crawlers that feed it.
 */
export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return buildRobots();
}
