import type { ReactNode } from "react";

import type { Address } from "@ai-web-agency/contracts";

import { content } from "@/lib/content";
import { formatAddress, formatIsoDate, mailtoHref, phoneHref } from "@/lib/format";
import { UI } from "@/lib/ui-strings";
import { Paragraphs, Section } from "./ui";

/**
 * Legal pages. The structure is statutory (DDG § 5, MStV § 18 (2), DSGVO Art. 13/14); every fact,
 * paragraph and link inside comes from the content artifact, which is why a site cannot even be
 * represented without Impressum and Datenschutz content (ADR-014).
 */

function LegalSection({
  id,
  heading,
  children,
}: {
  id: string;
  heading: string;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="mt-8">
      <h2 id={id} className="mb-3 text-xl font-semibold text-ink">
        {heading}
      </h2>
      {children}
    </section>
  );
}

function ExternalLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a className="underline hover:text-brand-700" href={href} rel="noopener noreferrer" target="_blank">
      {children}
    </a>
  );
}

function AddressBlock({ address, name }: { address: Address; name?: string }) {
  return (
    <address className="text-ink-muted">
      {name ? <p className="font-medium text-ink">{name}</p> : null}
      <p>{formatAddress(address)}</p>
    </address>
  );
}

function ContactLines({ phone, email }: { phone: string; email: string }) {
  return (
    <div className="space-y-1 text-ink-muted">
      <p>
        <strong className="font-medium text-ink">{UI.labelPhone}</strong>
        <a className="underline hover:text-brand-700" href={phoneHref(phone)}>
          {phone}
        </a>
      </p>
      <p>
        <strong className="font-medium text-ink">{UI.labelEmail}</strong>
        <a className="underline hover:text-brand-700" href={mailtoHref(email)}>
          {email}
        </a>
      </p>
    </div>
  );
}

/** DSGVO sections are `{ heading, paragraphs[] }` lists; one renderer keeps the pages consistent. */
function LegalSectionList({
  sections,
}: {
  sections: readonly { heading: string; paragraphs: readonly string[] }[];
}) {
  return (
    <div className="space-y-4">
      {sections.map((section) => (
        <div key={section.heading}>
          <h3 className="font-medium text-ink">{section.heading}</h3>
          <Paragraphs items={section.paragraphs} className="mt-1" />
        </div>
      ))}
    </div>
  );
}

export function ImprintView() {
  const { imprint } = content.legal;

  return (
    <Section labelledBy="legal-heading">
      <h1 id="legal-heading" className="text-3xl font-semibold text-ink">
        {UI.imprintHeading}
      </h1>

      <LegalSection id="imprint-provider" heading={UI.imprintProviderHeading}>
        <div className="space-y-2 text-ink-muted">
          <p className="font-medium text-ink">{imprint.provider_name}</p>
          <p>{imprint.legal_form}</p>
          <p>
            <strong className="font-medium text-ink">{UI.imprintRepresentedBy}: </strong>
            {imprint.represented_by.join(", ")}
          </p>
          <AddressBlock address={imprint.address} />
        </div>
      </LegalSection>

      <LegalSection id="imprint-contact" heading={UI.imprintContactHeading}>
        <ContactLines phone={imprint.contact.phone} email={imprint.contact.email} />
      </LegalSection>

      <LegalSection id="imprint-professional" heading={UI.imprintProfessionalHeading}>
        <div className="space-y-2 text-ink-muted">
          <p>{`${imprint.professional_title} (${imprint.professional_title_country})`}</p>
          <p>
            <ExternalLink href={imprint.professional_body.url}>
              {imprint.professional_body.name}
            </ExternalLink>
          </p>
          <p>
            <strong className="font-medium text-ink">{UI.labelSupervisingAuthority}</strong>
            {imprint.professional_body.supervising_authority}
          </p>
        </div>
      </LegalSection>

      <LegalSection id="imprint-regulations" heading={UI.imprintRegulationsHeading}>
        <ul className="space-y-1 text-ink-muted">
          {imprint.professional_regulations.map((regulation) => (
            <li key={regulation.name}>
              <ExternalLink href={regulation.url}>{regulation.name}</ExternalLink>
            </li>
          ))}
        </ul>
      </LegalSection>

      {imprint.vat_id ? (
        <LegalSection id="imprint-vat" heading={UI.imprintVatHeading}>
          <p className="text-ink-muted">{imprint.vat_id}</p>
        </LegalSection>
      ) : null}

      <LegalSection id="imprint-responsible" heading={UI.imprintResponsibleHeading}>
        <AddressBlock
          address={imprint.responsible_for_content.address}
          name={imprint.responsible_for_content.name}
        />
      </LegalSection>

      <LegalSection id="imprint-dispute" heading={UI.imprintDisputeHeading}>
        <Paragraphs items={imprint.dispute_resolution} />
      </LegalSection>

      <LegalSection id="imprint-liability" heading={UI.imprintLiabilityHeading}>
        <Paragraphs items={imprint.liability_notes} />
      </LegalSection>

      <LegalSection id="imprint-copyright" heading={UI.imprintCopyrightHeading}>
        <Paragraphs items={imprint.copyright_notes} />
      </LegalSection>

      <p className="mt-10 text-sm text-ink-muted">
        {UI.legalLastUpdatedPrefix}
        {formatIsoDate(imprint.last_updated)}
      </p>
    </Section>
  );
}

export function PrivacyView() {
  const { privacy } = content.legal;

  return (
    <Section labelledBy="legal-heading">
      <h1 id="legal-heading" className="text-3xl font-semibold text-ink">
        {UI.privacyHeading}
      </h1>

      <LegalSection id="privacy-controller" heading={UI.privacyControllerHeading}>
        <AddressBlock address={privacy.controller.address} name={privacy.controller.name} />
        <div className="mt-3">
          <ContactLines phone={privacy.controller_contact.phone} email={privacy.controller_contact.email} />
        </div>
      </LegalSection>

      {privacy.data_protection_officer ? (
        <LegalSection id="privacy-dpo" heading={UI.privacyDpoHeading}>
          <Paragraphs items={[privacy.data_protection_officer]} />
        </LegalSection>
      ) : null}

      <LegalSection id="privacy-hosting" heading={UI.privacyHostingHeading}>
        <div className="space-y-2 text-ink-muted">
          <p className="font-medium text-ink">{privacy.hosting.provider}</p>
          <p>{privacy.hosting.location}</p>
          <Paragraphs items={[privacy.hosting.note]} />
        </div>
      </LegalSection>

      <LegalSection id="privacy-legal-basis" heading={UI.privacyLegalBasisHeading}>
        <LegalSectionList sections={privacy.legal_basis} />
      </LegalSection>

      <LegalSection id="privacy-data-categories" heading={UI.privacyDataCategoriesHeading}>
        <LegalSectionList sections={privacy.data_categories} />
      </LegalSection>

      <LegalSection id="privacy-recipients" heading={UI.privacyRecipientsHeading}>
        <Paragraphs items={privacy.recipients} />
      </LegalSection>

      <LegalSection id="privacy-retention" heading={UI.privacyRetentionHeading}>
        <Paragraphs items={privacy.retention} />
      </LegalSection>

      <LegalSection id="privacy-rights" heading={UI.privacyRightsHeading}>
        <LegalSectionList sections={privacy.rights} />
      </LegalSection>

      <LegalSection id="privacy-cookies" heading={UI.privacyCookiesHeading}>
        <Paragraphs items={[privacy.cookies_notice]} />
      </LegalSection>

      <LegalSection id="privacy-form" heading={UI.privacyFormHeading}>
        <Paragraphs items={[privacy.contact_form_notice]} />
      </LegalSection>

      <LegalSection id="privacy-no-tracking" heading={UI.privacyNoTrackingHeading}>
        <Paragraphs items={[privacy.no_tracking_notice]} />
      </LegalSection>

      <LegalSection id="privacy-authority" heading={UI.privacyAuthorityHeading}>
        <div className="space-y-2 text-ink-muted">
          <p className="font-medium text-ink">
            <ExternalLink href={privacy.supervisory_authority.url}>
              {privacy.supervisory_authority.name}
            </ExternalLink>
          </p>
          <AddressBlock address={privacy.supervisory_authority.address} />
        </div>
      </LegalSection>

      <p className="mt-10 text-sm text-ink-muted">
        {UI.legalLastUpdatedPrefix}
        {formatIsoDate(privacy.last_updated)}
      </p>
    </Section>
  );
}


