import Link from "next/link";

import { content } from "@/lib/content";
import { Paragraphs, Section } from "./ui";

const PRIMARY_CTA_CLASS =
  "inline-flex items-center justify-center rounded-md bg-brand-600 px-5 py-3 text-base font-semibold text-surface hover:bg-brand-700";
const SECONDARY_CTA_CLASS =
  "inline-flex items-center justify-center rounded-md border border-brand-600 px-5 py-3 text-base font-semibold text-brand-700 hover:bg-brand-50";

/** Hero: single H1, with optional data-driven image/motion background. */
export function Hero() {
  const { hero } = content;
  const hasBackground = Boolean(hero.background_image || hero.background_video);

  return (
    <Section
      labelledBy="hero-heading"
      className="relative isolate overflow-hidden border-b border-line bg-brand-50 py-14 sm:py-20"
    >
      {hero.background_image ? (
        <div
          aria-hidden="true"
          className="absolute inset-0 -z-20 bg-cover bg-center"
          style={{ backgroundImage: `url(${hero.background_image})` }}
        />
      ) : null}
      {hero.background_video ? (
        <video
          aria-hidden="true"
          autoPlay
          muted
          loop
          playsInline
          poster={hero.background_image ?? undefined}
          className="hero-motion absolute inset-0 -z-10 h-full w-full object-cover"
        >
          <source src={hero.background_video} type="video/mp4" />
        </video>
      ) : null}
      {hasBackground ? (
        <div aria-hidden="true" className="absolute inset-0 -z-[5] bg-brand-50/85" />
      ) : null}

      <div className="relative">
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
      </div>
    </Section>
  );
}
