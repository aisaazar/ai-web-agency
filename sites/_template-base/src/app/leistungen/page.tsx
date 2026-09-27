import type { Metadata } from "next";

import { ContactSection } from "@/components/ContactSection";
import { JsonLd } from "@/components/JsonLd";
import { OpeningHours } from "@/components/OpeningHours";
import { PageIntro } from "@/components/PageIntro";
import { Services } from "@/components/Services";
import { buildPageMetadata } from "@/lib/seo";

export const metadata: Metadata = buildPageMetadata("/leistungen");

/** Detail page: the same Services component in its full variant, with per-service anchors. */
export default function ServicesPage() {
  return (
    <>
      <JsonLd pathname="/leistungen" />
      <PageIntro pathname="/leistungen" />
      <Services detailed />
      <OpeningHours />
      <ContactSection />
    </>
  );
}
