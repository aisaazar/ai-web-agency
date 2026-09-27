import type { Metadata } from "next";

import { JsonLd } from "@/components/JsonLd";
import { PrivacyView } from "@/components/LegalViews";
import { buildPageMetadata } from "@/lib/seo";

export const metadata: Metadata = buildPageMetadata("/datenschutz");

/** Datenschutzerklärung (DSGVO Art. 13/14). Required page — no build without it (ADR-014). */
export default function PrivacyPage() {
  return (
    <>
      <JsonLd pathname="/datenschutz" />
      <PrivacyView />
    </>
  );
}
