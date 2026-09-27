import { pageJsonLd, serializeJsonLd } from "@/lib/jsonld";

/**
 * Server-rendered JSON-LD. Rendered as a `<script>` text node from a deterministic serialiser, so
 * the codebase contains no `dangerouslySetInnerHTML` at all (docs/SECURITY-AND-RISKS.md) and the
 * markup can never contain more than the content artifact does.
 */
export function JsonLd({ pathname }: { pathname: string }) {
  const nodes = pageJsonLd(pathname);

  return (
    <>
      {nodes.map((node) => {
        const json = serializeJsonLd(node);
        return (
          <script key={json} type="application/ld+json">
            {json}
          </script>
        );
      })}
    </>
  );
}
