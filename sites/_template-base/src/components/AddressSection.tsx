import { content } from "@/lib/content";
import { phoneHref } from "@/lib/format";
import { Section, SectionHeading } from "./ui";

export function AddressSection() {
  const { business } = content;
  const { address, contact, map } = business;

  return (
    <Section id="adresse" labelledBy="address-heading">
      <SectionHeading id="address-heading" eyebrow="ADRESSE">
        Adresse & Anfahrt
      </SectionHeading>
      <div className="grid gap-8 lg:grid-cols-2">
        <address className="not-italic text-ink-muted">
          <p className="text-lg font-semibold text-ink">{business.brand_name}</p>
          <p className="mt-3">{address.street}</p>
          <p>{address.postal_code} {address.city}</p>
          <p>{address.region}, {address.country}</p>
          <div className="mt-5 space-y-2 text-sm">
            <p>
              <strong className="font-medium text-ink">Telefon: </strong>
              <a className="underline" href={phoneHref(contact.phone)}>{contact.phone}</a>
            </p>
            <p>
              <strong className="font-medium text-ink">E-Mail: </strong>
              <a className="underline" href={`mailto:${contact.email}`}>{contact.email}</a>
            </p>
          </div>
        </address>
        <div className="rounded-lg border border-line bg-surface-muted p-6">
          <h3 className="text-lg font-semibold text-ink">Anfahrt</h3>
          <p className="mt-3 text-sm text-ink-muted">{map.note}</p>
          <a
            href={map.link_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-5 inline-flex items-center justify-center rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-surface hover:bg-brand-700"
          >
            {map.link_label}
          </a>
        </div>
      </div>
    </Section>
  );
}
