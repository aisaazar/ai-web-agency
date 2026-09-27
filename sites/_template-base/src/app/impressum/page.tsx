import type { Metadata } from "next";

import { ImprintView } from "@/components/LegalViews";
import { JsonLd } from "@/components/JsonLd";
import { buildPageMetadata } from "@/lib/seo";

export const metadata: Metadata = buildPageMetadata("/impressum");

/** Impressum (DE: § 5 DDG, § 18 (2) MStV). Required page — no build without it (ADR-014). */
export default function ImprintPage() {
  return (
    <>
      <JsonLd pathname="/impressum" />
      <ImprintView />
    </>
  );
}
