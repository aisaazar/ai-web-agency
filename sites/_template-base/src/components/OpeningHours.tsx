import { content } from "@/lib/content";
import { formatSlots, formatWeekdays } from "@/lib/format";
import { UI } from "@/lib/ui-strings";
import { SECTION_ANCHORS } from "./SiteHeader";
import { Paragraphs, Section, SectionHeading } from "./ui";

/**
 * Opening hours plus the arrival facts (accessibility, parking, public transport). Facts a visitor
 * and an answer engine both need, straight from the content artifact.
 */
export function OpeningHours() {
  const { hours, business } = content;
  const { accessibility, map, parking, public_transport } = business;

  return (
    <Section id={SECTION_ANCHORS.hours} labelledBy="hours-heading">
      <SectionHeading id="hours-heading">{hours.heading}</SectionHeading>
      <Paragraphs items={hours.intro} />

      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        <div>
          <ul className="divide-y divide-line rounded-lg border border-line">
            {business.opening_hours.map((group) => (
              <li key={group.days.join("-")} className="flex flex-wrap justify-between gap-2 px-4 py-3">
                <span className="font-medium text-ink">{formatWeekdays(group.days)}</span>
                <span className="text-ink-muted">{formatSlots(group)}</span>
              </li>
            ))}
          </ul>
          {hours.appointment_note ? (
            <p className="mt-4 text-sm text-ink-muted">{hours.appointment_note}</p>
          ) : null}
          {hours.note ? <p className="mt-2 text-sm text-ink-muted">{hours.note}</p> : null}
        </div>

        <div className="space-y-6">
          <section aria-labelledby="arrival-heading">
            <h3 id="arrival-heading" className="mb-2 text-base font-semibold text-ink">
              {UI.arrivalHeading}
            </h3>
            <dl className="space-y-1 text-sm text-ink-muted">
              <div className="flex gap-2">
                <dt className="font-medium text-ink">{UI.accessibilityHeading}:</dt>
                <dd>
                  {UI.accessLabels.stepFree}: {accessibility.step_free_entrance ? UI.accessYes : UI.accessNo}
                  {", "}
                  {UI.accessLabels.elevator}: {accessibility.elevator ? UI.accessYes : UI.accessNo}
                  {", "}
                  {UI.accessLabels.accessibleToilet}:{" "}
                  {accessibility.accessible_toilet ? UI.accessYes : UI.accessNo}
                </dd>
              </div>
            </dl>
            {accessibility.notes ? (
              <p className="mt-2 text-sm text-ink-muted">{accessibility.notes}</p>
            ) : null}
            {parking ? (
              <p className="mt-2 text-sm text-ink-muted">
                <strong className="font-medium text-ink">{UI.parkingHeading}: </strong>
                {parking}
              </p>
            ) : null}
            {public_transport ? (
              <p className="mt-2 text-sm text-ink-muted">
                <strong className="font-medium text-ink">{UI.transportHeading}: </strong>
                {public_transport}
              </p>
            ) : null}
            {map.note ? <p className="mt-2 text-sm text-ink-muted">{map.note}</p> : null}
          </section>
        </div>
      </div>
    </Section>
  );
}
