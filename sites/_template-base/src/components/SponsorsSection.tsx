import { Section, SectionHeading } from "./ui";

const SPONSORS = [
  { id: "sponsor-01", name: "Sponsor 01", detail: "Logo-Platzhalter" },
  { id: "sponsor-02", name: "Sponsor 02", detail: "Logo-Platzhalter" },
  { id: "sponsor-03", name: "Sponsor 03", detail: "Logo-Platzhalter" },
] as const;

export function SponsorsSection() {
  return (
    <Section id="sponsoren" labelledBy="sponsors-heading" className="border-t border-line bg-surface-muted">
      <SectionHeading id="sponsors-heading" eyebrow="SPONSOREN">
        Unsere Sponsoren
      </SectionHeading>
      <p className="max-w-2xl text-ink-muted">
        Dieser Bereich ist für freigegebene Sponsor- und Partnerlogos vorgesehen.
      </p>
      <ul className="mt-8 grid gap-4 sm:grid-cols-3">
        {SPONSORS.map((sponsor) => (
          <li
            key={sponsor.id}
            className="flex min-h-28 flex-col items-center justify-center rounded-lg border border-dashed border-line bg-surface px-5 py-6 text-center"
          >
            <span className="text-base font-semibold text-ink">{sponsor.name}</span>
            <span className="mt-2 text-xs text-ink-muted">{sponsor.detail}</span>
          </li>
        ))}
      </ul>
    </Section>
  );
}
