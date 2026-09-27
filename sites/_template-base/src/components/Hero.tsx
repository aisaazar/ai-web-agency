import Link from "next/link";

import { content } from "@/lib/content";
import { Paragraphs, Section } from "./ui";

const PRIMARY_CTA_CLASS =
  "inline-flex items-center justify-center rounded-md bg-brand-600 px-5 py-3 text-base font-semibold text-surface hover:bg-brand-700";
const SECONDARY_CTA_CLASS =
  "inline-flex items-center justify-center rounded-md border border-brand-600 px-5 py-3 text-base font-semibold text-brand-700 hover:bg-brand-50";

/** Hero: the single `<h1>` of the home page, built from the content artifact, no copy in code. */
export function Hero() {
  const { hero } = content;

  return (
    <Section labelledBy="hero-heading" className="border-b border-line bg-brand-50 py-14 sm:py-20">
      {hero.eyebrow ? (
        <p className="mb-3 text-sm font-semibold tracking-wide text-brand-600 uppercase">
          {hero.eyebrow}
        </p>
      ) : null}
      <h1 id="hero-heading" className="max-w-3xl text-3xl font-semibold text-ink sm:text-4xl">
        {hero.headline}
      </h1>
      <p className="mt-4 max-w-2xl text-lg text-ink-muted">{hero.subheadline}</p>
      <Paragraphs items={hero.paragraphs} className="mt-6" />
      <div className="mt-8 flex flex-wrap gap-3">
        <Link href={hero.primary_cta.href} className={PRIMARY_CTA_CLASS}>
          {hero.primary_cta.label}
        </Link>
        {hero.secondary_cta ? (
          <Link href={hero.secondary_cta.href} className={SECONDARY_CTA_CLASS}>
            {hero.secondary_cta.label}
          </Link>
        ) : null}
      </div>
    </Section>
  );
}
