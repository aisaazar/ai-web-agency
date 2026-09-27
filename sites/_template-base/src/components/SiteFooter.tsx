import Link from "next/link";

import { content } from "@/lib/content";
import { formatAddress, formatIsoDate, formatSlots, formatWeekdays, mailtoHref, phoneHref } from "@/lib/format";
import { UI } from "@/lib/ui-strings";
import { Container } from "./ui";

/**
 * Footer: the legally required minimum plus the machine-readable facts an answer engine needs.
 * The medical disclaimer is rendered here on every page because `docs/PIPELINE-AND-GATE.md` marks
 * it as blocking for health categories.
 */
export function SiteFooter() {
  const { business, legal, compliance, site } = content;

  return (
    <footer className="mt-8 border-t border-line bg-surface-muted">
      <Container className="grid gap-8 py-12 sm:grid-cols-2 lg:grid-cols-3">
        <section aria-labelledby="footer-contact">
          <h2 id="footer-contact" className="mb-3 text-base font-semibold text-ink">
            {UI.footerContactHeading}
          </h2>
          <address className="space-y-1 text-sm text-ink-muted">
            <p className="font-medium text-ink">{business.legal_name}</p>
            <p>{formatAddress(business.address)}</p>
            <p>
              Telefon:{" "}
              <a className="underline hover:text-brand-700" href={phoneHref(business.contact.phone)}>
                {business.contact.phone}
              </a>
            </p>
            <p>
              E-Mail:{" "}
              <a className="underline hover:text-brand-700" href={mailtoHref(business.contact.email)}>
                {business.contact.email}
              </a>
            </p>
          </address>
        </section>

        <section aria-labelledby="footer-hours">
          <h2 id="footer-hours" className="mb-3 text-base font-semibold text-ink">
            {UI.footerHoursHeading}
          </h2>
          <ul className="space-y-1 text-sm text-ink-muted">
            {business.opening_hours.map((group) => (
              <li key={group.days.join("-")}>
                <span className="font-medium text-ink">{formatWeekdays(group.days)}</span>:{" "}
                {formatSlots(group)}
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="footer-legal">
          <h2 id="footer-legal" className="mb-3 text-base font-semibold text-ink">
            {UI.footerLegalHeading}
          </h2>
          <nav aria-label={UI.legalNav}>
            <ul className="space-y-1 text-sm">
              <li>
                <Link className="underline hover:text-brand-700" href="/impressum">
                  {UI.imprintLinkLabel}
                </Link>
              </li>
              <li>
                <Link className="underline hover:text-brand-700" href="/datenschutz">
                  {UI.privacyLinkLabel}
                </Link>
              </li>
            </ul>
          </nav>
          <p className="mt-3 text-sm text-ink-muted">
            {UI.footerUpdatedPrefix}
            {formatIsoDate(legal.imprint.last_updated)}
          </p>
        </section>
      </Container>

      <Container className="border-t border-line py-6">
        <section aria-labelledby="footer-disclaimer" className="mb-4">
          <h2 id="footer-disclaimer" className="mb-2 text-sm font-semibold text-ink">
            {UI.footerDisclaimerHeading}
          </h2>
          <div className="space-y-2 text-sm text-ink-muted">
            {compliance.medical_disclaimer.map((paragraph) => (
              <p key={paragraph.slice(0, 40)}>{paragraph}</p>
            ))}
          </div>
        </section>
        <p className="text-sm text-ink-muted">
          © {business.legal_name} · {site.url.replace(/^https?:\/\//u, "").replace(/\/$/u, "")}
        </p>
      </Container>
    </footer>
  );
}
