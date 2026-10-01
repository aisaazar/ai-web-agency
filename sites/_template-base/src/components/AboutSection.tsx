import { content } from "@/lib/content";
import { Section, SectionHeading } from "./ui";

export function AboutSection() {
  const owner = content.team.members[0];

  return (
    <Section id="ueber-uns" labelledBy="about-heading" className="bg-surface-muted">
      <SectionHeading id="about-heading" eyebrow="ÜBER UNS">
        Über uns
      </SectionHeading>
      <div className="grid gap-8 lg:grid-cols-[1.5fr_1fr] lg:items-start">
        <div className="space-y-4 text-ink-muted">
          <p>{content.site.description}</p>
          {content.team.intro.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
        <div className="rounded-lg border border-line bg-surface p-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-brand-600">Praxisinhaber</p>
          <h3 className="mt-2 text-xl font-semibold text-ink">{owner.name}</h3>          <p className="mt-1 text-sm font-medium text-brand-700">{owner.role}</p>
          {owner.bio.map((paragraph) => (
            <p key={paragraph} className="mt-3 text-sm text-ink-muted">{paragraph}</p>
          ))}
          {owner.focus_areas?.length ? (
            <p className="mt-3 text-sm text-ink-muted">
              <strong className="font-medium text-ink">Schwerpunkte: </strong>
              {owner.focus_areas.join(", ")}
            </p>
          ) : null}
        </div>
      </div>
    </Section>
  );
}
