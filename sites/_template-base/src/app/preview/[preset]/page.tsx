import { AboutSection } from "@/components/AboutSection";
import { AddressSection } from "@/components/AddressSection";
import { ContactSection } from "@/components/ContactSection";
import { Faq } from "@/components/Faq";
import { Hero } from "@/components/Hero";
import { Highlights } from "@/components/Highlights";
import { MediaSection } from "@/components/MediaSection";
import { OpeningHours } from "@/components/OpeningHours";
import { Services } from "@/components/Services";
import { Team } from "@/components/Team";
import { TreatmentExperience } from "@/components/TreatmentExperience";

const PRESETS = ["health", "corporate", "warm"] as const;
type Preset = (typeof PRESETS)[number];

export function generateStaticParams(): Array<{ preset: Preset }> {
  return PRESETS.map((preset) => ({ preset }));
}

export const dynamicParams = false;

type Props = {
  params: Promise<{ preset: string }>;
};

function normalizePreset(value: string): Preset {
  return PRESETS.includes(value as Preset) ? value as Preset : "health";
}

export default async function PreviewPage({ params }: Props) {
  const { preset } = await params;
  const selected = normalizePreset(preset);

  return (
    <div className={"preview-shell preview-theme-" + selected} data-preview-preset={selected}>
      <div className="preview-banner">
        <span>AI Web Agency Preview</span>
        <strong>{selected}</strong>
        <span>Same content · same components · alternate art direction</span>
      </div>
      <Hero />
      <section aria-label="Highlights" className="py-10 sm:py-14">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8"><Highlights /></div>
      </section>
      <Services />
      <TreatmentExperience />
      <AboutSection />
      <Team />
      <AddressSection />
      <OpeningHours />
      <Faq />
      <ContactSection />
      <MediaSection />
    </div>
  );
}

