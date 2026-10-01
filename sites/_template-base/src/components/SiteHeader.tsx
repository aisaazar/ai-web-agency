import Link from "next/link";

import { content } from "@/lib/content";
import { phoneHref } from "@/lib/format";
import { UI } from "@/lib/ui-strings";
import { Container } from "./ui";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { SiteNav, type NavItem } from "./SiteNav";

/** Anchor targets that exist on the home page. Kept here so nav and page cannot drift apart. */
export const SECTION_ANCHORS = {
  team: "team",
  hours: "oeffnungszeiten",
  services: "leistungen",
  faq: "fragen",
  contact: "kontakt",
  about: "ueber-uns",
  address: "adresse",
  media: "medien",
} as const;

export const NAV_ITEMS: readonly NavItem[] = [
  { href: "/", label: "Start" },
  { href: "/leistungen", label: "Leistungen" },
  { href: `/#${SECTION_ANCHORS.about}`, label: "Über uns" },
  { href: `/#${SECTION_ANCHORS.team}`, label: "Team" },
  { href: `/#${SECTION_ANCHORS.hours}`, label: "Sprechzeiten" },
  { href: `/#${SECTION_ANCHORS.address}`, label: "Adresse" },
  { href: `/#${SECTION_ANCHORS.contact}`, label: "Kontakt" },
  { href: `/#${SECTION_ANCHORS.media}`, label: "Medien" },
];

export function SiteHeader() {
  const { site, business } = content;

  return (
    <header className="border-b border-line bg-surface">
      <Container className="flex flex-col gap-4 py-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <Link href="/" className="text-lg font-semibold text-ink hover:text-brand-700">
            {site.short_name ?? site.name}
          </Link>
          <p className="text-sm text-ink-muted">{site.tagline}</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-6">
          <SiteNav items={NAV_ITEMS} ariaLabel={UI.primaryNav} />
          <LanguageSwitcher />
          <a
            href={phoneHref(business.contact.phone)}
            className="inline-flex items-center justify-center rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-surface hover:bg-brand-700"
          >
            {business.contact.phone}
          </a>
        </div>
      </Container>
    </header>
  );
}
