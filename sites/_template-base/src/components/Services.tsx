import Link from "next/link";

import { content } from "@/lib/content";
import { UI } from "@/lib/ui-strings";
import { SECTION_ANCHORS } from "./SiteHeader";
import { Icon } from "./Icon";
import { Paragraphs, Section, SectionHeading } from "./ui";

/**
 * Services section, rendered twice with different depth: as a preview on the home page (summary plus
 * a link to the detail anchor) and in full on `/leistungen`. Same component, same content model —
 * a per-client template fork is exactly what ADR-016 forbids.
 */
export function Services({ detailed = false }: { detailed?: boolean }) {
  const { services } = content;

  return (
    <Section id={SECTION_ANCHORS.services} labelledBy="services-heading">
      <SectionHeading id="services-heading" eyebrow="Leistungen">
        {services.heading}
      </SectionHeading>
      <Paragraphs items={services.intro} />

      <ul className="mt-10 grid gap-4 sm:grid-cols-2">
        {services.items.map((service) => {
          const features = service.features ?? [];
          return (
          <li
            key={service.id}
            id={detailed ? service.id : undefined}
            className="motion-card group p-6 sm:p-7"
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-700 transition-transform duration-500 group-hover:rotate-6 group-hover:scale-105">
                <Icon name={service.icon} />
              </span>
              <h3 className="font-display text-2xl font-normal tracking-[-0.02em] text-ink">{service.title}</h3>
            </div>
            <p className="mt-3 text-ink-muted">{service.summary}</p>

            {detailed ? (
              <>
                <Paragraphs items={service.paragraphs} className="mt-4" />
                {features.length > 0 ? (
                  <ul className="mt-4 space-y-2 text-sm text-ink-muted">
                    {features.map((feature) => (
                      <li key={feature} className="flex gap-2">
                        <span aria-hidden="true" className="text-brand-600">
                          •
                        </span>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : (
              <Link
                href={`/leistungen#${service.id}`}
                className="mt-4 inline-block text-sm font-semibold text-brand-700 underline underline-offset-4 hover:text-brand-600"
              >
                {UI.detailsAbout(service.title)}
              </Link>
            )}
          </li>
          );
        })}
      </ul>

      {services.note ? <p className="mt-6 text-sm text-ink-muted">{services.note}</p> : null}
    </Section>
  );
}
