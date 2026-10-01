import Image from "next/image";
import Link from "next/link";

import { content } from "@/lib/content";
import { LanguageSwitcher } from "./LanguageSwitcher";

const NAV_LINKS = [
  ["Studio", "#leistungen"],
  ["Method", "#experience"],
  ["People", "#team"],
  ["Contact", "#kontakt"],
] as const;

const FALLBACK_POSTER = "/media/dental-clinic-hero.jpg";

export function Hero() {
  const hero = content.hero;
  const posterSource = hero.background_image || FALLBACK_POSTER;
  const ctaHref = hero.primary_cta?.href || "#kontakt";

  return (
    <section id="home" aria-labelledby="hero-heading" className="cinematic-hero relative min-h-[100svh] overflow-hidden bg-[#071114] text-white">
      <Image
        src={posterSource}
        alt=""
        aria-hidden="true"
        fill
        priority
        sizes="100vw"
        className="hero-poster-motion object-cover"
      />
      <video className="hero-video absolute inset-0 z-0 h-full w-full object-cover" autoPlay muted loop playsInline poster={posterSource} aria-hidden="true">
        <source src="/media/praxis-demo.mp4" type="video/mp4" />
      </video>
      <div className="hero-veil absolute inset-0 z-[1]" />
      <div className="hero-orbit hero-orbit-one" aria-hidden="true" />
      <div className="hero-orbit hero-orbit-two" aria-hidden="true" />

      <div className="relative z-10 flex min-h-[100svh] flex-col">
        <nav aria-label="Primary navigation" className="mx-auto mt-4 flex w-[calc(100%-1.5rem)] max-w-7xl items-center justify-between rounded-full border border-white/15 bg-black/10 px-4 py-3 backdrop-blur-xl md:mt-6 md:px-6">
          <Link href="#home" className="font-display text-2xl tracking-[-0.04em]">
            {content.site.short_name ?? content.site.name}<sup className="ml-0.5 align-super text-[9px]">®</sup>
          </Link>
          <div className="hidden items-center gap-8 md:flex">
            {NAV_LINKS.map(([label, href]) => (
              <Link key={label} href={href} className="text-[11px] uppercase tracking-[0.18em] text-white/65 transition hover:text-white">
                {label}
              </Link>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <Link href={ctaHref} className="hidden rounded-full bg-white px-5 py-2.5 text-xs font-semibold uppercase tracking-[0.14em] text-[#071114] transition-transform hover:-translate-y-0.5 sm:inline-flex">
              {hero.primary_cta?.label ?? "Termin anfragen"}
            </Link>
          </div>
        </nav>
        <div className="flex flex-1 items-end px-5 pb-10 pt-20 sm:px-8 sm:pb-14 lg:px-12 lg:pb-20">
          <div className="grid w-full gap-10 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.55fr)] lg:items-end">
            <div className="max-w-5xl">
              <p className="animate-fade-rise text-[10px] font-semibold uppercase tracking-[0.28em] text-white/60">
                {hero.eyebrow ?? "Modern dentistry / Nürnberg"}
              </p>
              <h1 id="hero-heading" className="animate-fade-rise-delay mt-5 max-w-4xl font-display text-[clamp(3.5rem,9vw,8.6rem)] leading-[0.84] tracking-[-0.055em] text-balance">
                {hero.headline}
              </h1>
              <p className="animate-fade-rise-delay-2 mt-7 max-w-xl text-sm leading-7 text-white/70 sm:text-base">
                {hero.subheadline}
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link href={ctaHref} className="rounded-full bg-white px-6 py-3 text-sm font-semibold text-[#071114] transition-transform hover:-translate-y-0.5">
                  {hero.primary_cta?.label ?? "Termin anfragen"}
                </Link>
                <Link href={hero.secondary_cta?.href ?? "#leistungen"} className="rounded-full border border-white/25 px-6 py-3 text-sm text-white/85 backdrop-blur transition hover:border-white/50 hover:bg-white/5">
                  {hero.secondary_cta?.label ?? "Leistungen ansehen"}
                </Link>
              </div>
            </div>
            <div className="hidden justify-self-end lg:block">
              <div className="glass-panel max-w-sm p-5">
                <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-white/45">
                  <span>Approach</span><span>01 / 04</span>
                </div>
                <p className="mt-5 font-display text-3xl leading-none">Precision, without the clinical coldness.</p>
                <div className="mt-6 h-px bg-white/15" />
                <p className="mt-4 text-xs leading-6 text-white/55">A quiet digital experience for modern dental care, informed by motion design, editorial layouts and interactive 3D cues.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
