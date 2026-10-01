import { content } from "@/lib/content";
import { initials } from "@/lib/format";
import { UI } from "@/lib/ui-strings";
import { SECTION_ANCHORS } from "./SiteHeader";
import { Paragraphs, Section, SectionHeading } from "./ui";

/**
 * Team section. `photo_url` is nullable by design: a client photo that has not been approved yet
 * renders initials, so an unapproved image can never appear on a live site.
 */
export function Team() {
  const { team } = content;

  return (
    <Section id={SECTION_ANCHORS.team} labelledBy="team-heading" className="bg-surface-muted">
      <SectionHeading id="team-heading">{team.heading}</SectionHeading>
      <Paragraphs items={team.intro} />

      <ul className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {team.members.map((member) => {
          const focusAreas = member.focus_areas ?? [];
          return (
          <li key={member.id} className="motion-card group p-6 sm:p-7">
            <div
              aria-hidden="true"
              className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-base font-semibold text-brand-700"
            >
              {initials(member.name)}
            </div>
            <h3 className="text-base font-semibold text-ink">{member.name}</h3>
            <p className="text-sm font-medium text-brand-700">{member.role}</p>
            <ul className="mt-3 space-y-1 text-sm text-ink-muted">
              {member.qualifications.map((qualification) => (
                <li key={qualification}>{qualification}</li>
              ))}
            </ul>
            {focusAreas.length > 0 ? (
              <p className="mt-3 text-sm text-ink-muted">
                <strong className="font-medium text-ink">{UI.labelFocusAreas}</strong>
                {focusAreas.join(", ")}
              </p>
            ) : null}
            <Paragraphs items={member.bio} className="mt-3 text-sm" />
            <p className="mt-3 text-sm text-ink-muted">
              <strong className="font-medium text-ink">{UI.labelLanguages}</strong>
              {member.languages.join(", ")}
            </p>
          </li>
          );
        })}
      </ul>
    </Section>
  );
}
