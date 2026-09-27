import Link from "next/link";

import { content } from "@/lib/content";
import { UI } from "@/lib/ui-strings";
import { Section } from "@/components/ui";

export const metadata = {
  title: `404 – ${content.site.short_name ?? content.site.name}`,
  robots: { index: false, follow: false },
};

/** Exported as `404.html`: a static export must still explain itself without a server. */
export default function NotFound() {
  return (
    <Section labelledBy="page-heading">
      <h1 id="page-heading" className="text-3xl font-semibold text-ink">
        {UI.notFoundHeading}
      </h1>
      <p className="mt-3 text-ink-muted">{UI.notFoundBody}</p>
      <p className="mt-6">
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-md bg-brand-600 px-5 py-3 text-base font-semibold text-surface hover:bg-brand-700"
        >
          {UI.backToHome}
        </Link>
      </p>
    </Section>
  );
}
