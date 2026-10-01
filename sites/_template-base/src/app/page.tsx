import type { Metadata } from "next";

import { AboutSection } from "@/components/AboutSection";
import { AddressSection } from "@/components/AddressSection";
import { AgentWidget } from "@/components/AgentWidget";
import { ContactSection } from "@/components/ContactSection";
import { Faq } from "@/components/Faq";
import { Hero } from "@/components/Hero";
import { Highlights } from "@/components/Highlights";
import { MediaSection } from "@/components/MediaSection";
import { JsonLd } from "@/components/JsonLd";
import { OpeningHours } from "@/components/OpeningHours";
import { Services } from "@/components/Services";
import { SponsorsSection } from "@/components/SponsorsSection";
import { Team } from "@/components/Team";
import { TreatmentExperience } from "@/components/TreatmentExperience";
import { buildPageMetadata } from "@/lib/seo";

export const metadata: Metadata = buildPageMetadata("/");
const agentEnabled = Boolean(
  process.env.NEXT_PUBLIC_AGENCY_AGENT_API_URL && process.env.NEXT_PUBLIC_AGENCY_CLIENT_ID,
);

export default function HomePage() {
  return (
    <>
      <JsonLd pathname="/" />
      <Hero />
      <section aria-label="Highlights" className="py-10 sm:py-14">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <Highlights />
        </div>
      </section>
      <div className="marquee border-y border-line bg-surface py-4">
        <div className="marquee-track gap-8 whitespace-nowrap text-[10px] font-semibold uppercase tracking-[0.28em] text-ink-muted">
          <span>Preventive care</span><span>✦</span><span>Digital diagnostics</span><span>✦</span><span>Aesthetic dentistry</span><span>✦</span><span>Calm treatment</span><span>✦</span>
          <span aria-hidden="true">Preventive care</span><span aria-hidden="true">✦</span><span aria-hidden="true">Digital diagnostics</span><span aria-hidden="true">✦</span><span aria-hidden="true">Aesthetic dentistry</span><span aria-hidden="true">✦</span><span aria-hidden="true">Calm treatment</span><span aria-hidden="true">✦</span>
        </div>
      </div>
      <Services />
      <TreatmentExperience />
      <AboutSection />
      <Team />
      <AddressSection />
      <OpeningHours />
      <Faq />
      <ContactSection />
      <MediaSection />
      <SponsorsSection />
      {agentEnabled ? <AgentWidget /> : null}
    </>
  );
}
