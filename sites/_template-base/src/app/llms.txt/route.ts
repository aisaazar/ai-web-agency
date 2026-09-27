import { buildLlmsTxt } from "@/lib/manifests";

/**
 * `/llms.txt` — the plain-text summary for AI answer engines, generated from the same content
 * artifact as the HTML. Static route handler: no request-time work, so `output: "export"` can emit
 * it as a real file.
 */
export const dynamic = "force-static";

export function GET(): Response {
  return new Response(buildLlmsTxt(), {
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=0, must-revalidate",
    },
  });
}
