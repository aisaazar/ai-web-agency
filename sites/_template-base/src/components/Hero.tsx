import Link from "next/link";

import { content } from "@/lib/content";
import { LanguageSwitcher } from "./LanguageSwitcher";

const NAV_LINKS = [
  ["Home", "#home"],
  ["Studio", "#leistungen"],
  ["About", "#ueber-uns"],
  ["Journal", "#medien"],
  ["Reach Us", "#kontakt"],
] as const;

const FALLBACK_VIDEO = "/media/velorah-hero.mp4";
const FALLBACK_POSTER = "/media/dental-clinic-hero.jpg";

export function Hero() {
  const hero = content.hero;
  const videoSource = hero.background_video || FALLBACK_VIDEO;
  const posterSource = hero.background_image || FALLBACK_POSTER;
  const ctaHref = hero.primary_cta?.href || "#kontakt";

  return (
    <section id="home" aria-labelledby="hero-heading" className="cinematic-hero relative min-h-screen overflow-hidden bg-[hsl(var(--background))] text-[hsl(var(--foreground))]">
      <video
        aria-hidden="true"
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        poster={posterSource}
        className="hero-video absolute inset-0 z-0 h-full w-full object-cover"
      >
        <source src={videoSource} type="video/mp4" />
      </video>

      <div className="relative z-10 flex min-h-screen flex-col">
        <nav aria-label="Primary navigation" className="liquid-glass mx-auto mt-5 flex w-[calc(100%-2rem)] max-w-7xl items-center justify-between rounded-full px-5 py-3 md:mt-6 md:px-8">
          <div className="flex w-full items-center justify-between gap-6">
            <Link href="#home" className="shrink-0 text-3xl tracking-tight text-[hsl(var(--foreground))]" style={{ fontFamily: "'Instrument Serif', serif" }}>
              Velorah<sup className="ml-0.5 text-xs">®</sup>
            </Link>
            <div className="hidden items-center gap-7 md:flex">
              {NAV_LINKS.map(([label, href], index) => (
                <Link
                  key={label}
                  href={href}
                  aria-current={index === 0 ? "page" : undefined}
                  className="text-sm text-[hsl(var(--muted-foreground))] transition-colors hover:text-[hsl(var(--foreground))]"
                >
                  {label}
                </Link>
              ))}
            </div>
            <div className="flex items-center gap-2 sm:gap-3">
              <LanguageSwitcher />
              <Link href={ctaHref} className="liquid-glass hidden rounded-full px-5 py-2.5 text-sm text-[hsl(var(--foreground))] transition-transform hover:scale-[1.03] sm:inline-flex">
                Begin Journey
              </Link>
            </div>
          </div>
        </nav>

        <div className="flex flex-1 items-center justify-center px-6 pb-28 pt-20 text-center md:pb-36 md:pt-24">
          <div className="mx-auto max-w-7xl">
            <h1 id="hero-heading" className="animate-fade-rise font-normal leading-[0.95] tracking-[-2.46px] text-[hsl(var(--foreground))] text-5xl sm:text-7xl md:text-8xl" style={{ fontFamily: "'Instrument Serif', serif" }}>
              Where <em className="not-italic text-[hsl(var(--muted-foreground))]">dreams</em> rise <em className="not-italic text-[hsl(var(--muted-foreground))]">through the silence.</em>
            </h1>
            <p className="animate-fade-rise-delay mx-auto mt-8 max-w-2xl text-base leading-relaxed text-[hsl(var(--muted-foreground))] sm:text-lg">
              We&apos;re designing tools for deep thinkers, bold creators, and quiet rebels. Amid the chaos, we build digital spaces for sharp focus and inspired work.
            </p>
            <Link href={ctaHref} className="liquid-glass animate-fade-rise-delay-2 mt-12 inline-flex rounded-full px-14 py-5 text-base text-[hsl(var(--foreground))] transition-transform hover:scale-[1.03]">
              Begin Journey
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
