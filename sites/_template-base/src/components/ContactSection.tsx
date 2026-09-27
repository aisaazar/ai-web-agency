import { content } from "@/lib/content";
import { formatAddress, mailtoHref, phoneHref } from "@/lib/format";
import { UI } from "@/lib/ui-strings";
import { LeadForm } from "./LeadForm";
import { SECTION_ANCHORS } from "./SiteHeader";
import { Paragraphs, Section, SectionHeading } from "./ui";

/**
 * Contact section: channels (click-through, no embed) plus the lead form. The map is an ordinary
 * link, not an iframe, so nothing third-party loads before a visitor chooses to leave the site
 * (docs/SECURITY-AND-RISKS.md, cookie consent).
 */
export function ContactSection() {
  const { contact, business } = content;
  const { contact: details, map } = business;

  return (
    <Section id={SECTION_ANCHORS.contact} labelledBy="contact-heading">
      <SectionHeading id="contact-heading">{contact.heading}</SectionHeading>
      <Paragraphs items={contact.intro} />

      <div className="mt-10 grid gap-10 lg:grid-cols-2">
        <section aria-labelledby="channels-heading">
          <h3 id="channels-heading" className="mb-4 text-lg font-semibold text-ink">
            {contact.channels_heading}
          </h3>
          <address className="space-y-2 text-ink-muted">
            <p>{formatAddress(business.address)}</p>
            <p>
              <strong className="font-medium text-ink">{UI.labelPhone}</strong>
              <a className="underline hover:text-brand-700" href={phoneHref(details.phone)}>
                {details.phone}
              </a>
            </p>
            <p>
              <strong className="font-medium text-ink">{UI.labelEmail}</strong>
              <a className="underline hover:text-brand-700" href={mailtoHref(details.email)}>
                {details.email}
              </a>
            </p>
          </address>

          {details.emergency_phone ? (
            <div className="mt-6 rounded-lg border border-accent-600 bg-accent-100 p-4">
              <h4 className="text-sm font-semibold text-accent-700">
                {`${UI.emergencyHeading}: ${details.emergency_phone}`}
              </h4>
              {details.emergency_note ? (
                <p className="mt-2 text-sm text-accent-700">{details.emergency_note}</p>
              ) : null}
            </div>
          ) : null}

          <p className="mt-6 text-sm">
            <a
              className="font-semibold text-brand-700 underline underline-offset-4 hover:text-brand-600"
              href={map.link_url}
              rel="noopener noreferrer"
            >
              {map.link_label}
            </a>
          </p>
          {map.note ? <p className="mt-2 text-sm text-ink-muted">{map.note}</p> : null}
          {contact.reply_note ? (
            <p className="mt-6 text-sm text-ink-muted">{contact.reply_note}</p>
          ) : null}
        </section>

        <section aria-labelledby="lead-form-heading">
          <h3 id="lead-form-heading" className="text-lg font-semibold text-ink">
            {contact.form.heading}
          </h3>
          <Paragraphs items={contact.form.intro} className="mt-3" />
          <LeadForm form={contact.form} />
        </section>
      </div>
    </Section>
  );
}
