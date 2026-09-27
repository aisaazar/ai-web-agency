import { pageSeo } from "@/lib/content";
import { Section } from "./ui";

/**
 * Page header for the secondary pages: the `<h1>` and lead paragraph come straight from the SEO
 * manifest entry, so the visible page and its `<title>`/`<meta name="description">` can never drift
 * apart. Exactly one `<h1>` per page (checked by `scripts/validate-output.mjs`).
 */
export function PageIntro({ pathname }: { pathname: string }) {
  const page = pageSeo(pathname);

  return (
    <Section labelledBy="page-heading" className="border-b border-line bg-brand-50">
      <h1 id="page-heading" className="max-w-3xl text-3xl font-semibold text-balance text-ink">
        {page.title}
      </h1>
      <p className="mt-3 max-w-2xl text-lg text-ink-muted">{page.description}</p>
    </Section>
  );
}
