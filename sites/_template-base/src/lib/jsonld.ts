/**
 * JSON-LD builders. Deterministic code over typed, approved content — never a model authoring
 * structured data (ADR-013; a hallucinated rating or price in schema.org markup is a deindexing
 * risk, not a stylistic one).
 *
 * Every value here traces back to a field of the content artifact, so the markup cannot claim more
 * than the site says. `scripts/validate-output.mjs` asserts exactly that on the built HTML.
 */
import type { Business } from "@ai-web-agency/contracts";

import { absoluteUrl, content, origin } from "./content";

type Weekday = "Mo" | "Tu" | "We" | "Th" | "Fr" | "Sa" | "Su";

export type JsonLdNode = Record<string, unknown>;

/** Allowlisted content category -> schema.org type (ADR-013: no free-form type from a model). */
const JSONLD_TYPE_BY_BUSINESS_TYPE: Record<Business["business_type"], string> = {
  dental_clinic: "Dentist",
};

const SCHEMA_DAY: Record<Weekday, string> = {
  Mo: "Monday",
  Tu: "Tuesday",
  We: "Wednesday",
  Th: "Thursday",
  Fr: "Friday",
  Sa: "Saturday",
  Su: "Sunday",
};

function postalAddress(): JsonLdNode {
  const { address } = content.business;
  return {
    "@type": "PostalAddress",
    streetAddress: address.street,
    postalCode: address.postal_code,
    addressLocality: address.city,
    ...(address.region ? { addressRegion: address.region } : {}),
    addressCountry: address.country,
  };
}

function openingHoursSpecification(): JsonLdNode[] {
  return content.business.opening_hours.flatMap((group) =>
    group.slots.map((slot) => ({
      "@type": "OpeningHoursSpecification",
      dayOfWeek: group.days.map((day) => SCHEMA_DAY[day]),
      opens: slot.opens,
      closes: slot.closes,
    })),
  );
}

export function businessJsonLd(): JsonLdNode {
  const { business, site } = content;
  const { contact, geo } = business;

  return {
    "@context": "https://schema.org",
    "@type": JSONLD_TYPE_BY_BUSINESS_TYPE[business.business_type],
    "@id": `${origin}/#praxis`,
    name: business.brand_name,
    legalName: business.legal_name,
    url: origin,
    description: site.description,
    telephone: contact.phone,
    email: contact.email,
    ...(contact.emergency_phone ? { emergencyPhone: contact.emergency_phone } : {}),
    address: postalAddress(),
    geo: {
      "@type": "GeoCoordinates",
      latitude: geo.latitude,
      longitude: geo.longitude,
    },
    openingHoursSpecification: openingHoursSpecification(),
    availableLanguage: business.spoken_languages,
    paymentAccepted: business.payment_methods.join(", "),
    ...(business.price_range ? { priceRange: business.price_range } : {}),
    inLanguage: content.locale,
  };
}

export function websiteJsonLd(): JsonLdNode {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "@id": `${origin}/#website`,
    url: `${origin}/`,
    name: content.site.name,
    description: content.site.description,
    inLanguage: content.locale,
    publisher: { "@id": `${origin}/#praxis` },
  };
}

export function faqJsonLd(): JsonLdNode {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "@id": `${origin}/#faq`,
    inLanguage: content.locale,
    mainEntity: content.faq.items.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer.join(" "),
      },
    })),
  };
}

export function webPageJsonLd(pathname: string): JsonLdNode {
  const page = content.seo.pages.find((candidate) => candidate.path === pathname);
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "@id": `${absoluteUrl(pathname)}#webpage`,
    url: absoluteUrl(pathname),
    name: page?.title ?? content.site.name,
    description: page?.description ?? content.site.description,
    inLanguage: content.locale,
    isPartOf: { "@id": `${origin}/#website` },
    about: { "@id": `${origin}/#praxis` },
  };
}

export function breadcrumbJsonLd(pathname: string): JsonLdNode {
  const page = content.seo.pages.find((candidate) => candidate.path === pathname);
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "@id": `${absoluteUrl(pathname)}#breadcrumb`,
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: content.site.short_name ?? content.site.name,
        item: `${origin}/`,
      },
      {
        "@type": "ListItem",
        position: 2,
        name: page?.title ?? pathname,
        item: absoluteUrl(pathname),
      },
    ],
  };
}

/** All JSON-LD nodes for one page, in a fixed order so the HTML is byte-stable across builds. */
export function pageJsonLd(pathname: string): JsonLdNode[] {
  const nodes: JsonLdNode[] = [businessJsonLd(), websiteJsonLd()];
  if (pathname === "/") {
    nodes.push(faqJsonLd());
  }
  nodes.push(webPageJsonLd(pathname));
  if (pathname !== "/") {
    nodes.push(breadcrumbJsonLd(pathname));
  }
  return nodes;
}

/**
 * Serialise for a `<script type="application/ld+json">` text node. `<` is escaped so the JSON can
 * never terminate the script element early — the reason the codebase needs no
 * `dangerouslySetInnerHTML` anywhere (docs/SECURITY-AND-RISKS.md).
 */
export function serializeJsonLd(node: JsonLdNode): string {
  return JSON.stringify(node).replace(/</gu, "\\u003c");
}
