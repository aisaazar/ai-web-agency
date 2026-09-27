import type { Metadata } from "next";

import { ContactSection } from "@/components/ContactSection";
import { Faq } from "@/components/Faq";
import { Hero } from "@/components/Hero";
import { Highlights } from "@/components/Highlights";
import { JsonLd } from "@/components/JsonLd";
import { OpeningHours } from "@/components/OpeningHours";
import { Services } from "@/components/Services";
import { Team } from "@/components/Team";
import { buildPageMetadata } from "@/lib/seo";

export const metadata: Metadata = buildPageMetadata("/");

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
      <Services />
      <Team />
      <OpeningHours />
      <Faq />
      <ContactSection />
    </>
  );
}
