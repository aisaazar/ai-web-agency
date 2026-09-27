/**
 * Site manifests: sitemap.xml, robots.txt and llms.txt.
 *
 * All three are pure functions of the content artifact. Nothing reads the clock, the environment or
 * a network, so the same artifact revision always produces byte-identical output — which is what
 * makes `build_hash` a meaningful identity for a deploy and a rollback (docs/DOMAIN-MODEL.md).
 */
import type { MetadataRoute } from "next";

import { absoluteUrl, content, origin } from "./content";
import { formatAddress, formatSlots, formatWeekdays } from "./format";

/** Crawlers that feed AI answer engines. An AI-readable site that blocks them is self-defeating. */
const AI_CRAWLERS = [
  "GPTBot",
  "OAI-SearchBot",
  "ChatGPT-User",
  "ClaudeBot",
  "Claude-User",
  "PerplexityBot",
  "Google-Extended",
  "CCBot",
  "Applebot-Extended",
  "meta-externalagent",
] as const;

const CHANGE_FREQUENCY: Record<string, "yearly" | "monthly" | "weekly"> = {
  "/": "weekly",
  "/leistungen": "monthly",
  "/impressum": "yearly",
  "/datenschutz": "yearly",
};

const PRIORITY: Record<string, number> = {
  "/": 1,
  "/leistungen": 0.8,
  "/impressum": 0.3,
  "/datenschutz": 0.3,
};

export function buildSitemap(): MetadataRoute.Sitemap {
  return content.seo.pages
    .filter((page) => page.noindex !== true)
    .map((page) => ({
      url: absoluteUrl(page.path),
      // Content-provided date, never "now": a rebuild of unchanged content must not look like a
      // content change to a crawler.
      lastModified: content.legal.imprint.last_updated,
      changeFrequency: CHANGE_FREQUENCY[page.path] ?? "monthly",
      priority: PRIORITY[page.path] ?? 0.5,
    }));
}

export function buildRobots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/" },
      ...AI_CRAWLERS.map((userAgent) => ({ userAgent, allow: "/" })),
    ],
    sitemap: `${origin}/sitemap.xml`,
    host: origin,
  };
}

/**
 * llms.txt: the machine-readable summary an answer engine can quote without guessing.
 * Deliberately plain text, deliberately derived only from approved content fields, and it carries
 * the medical disclaimer so the model quotes the caveat with the facts.
 */
export function buildLlmsTxt(): string {
  const { site, business, faq, compliance, hours } = content;
  const pages = content.seo.pages.filter((page) => page.noindex !== true);
  const services = content.services.items;

  const lines: string[] = [
    `# ${site.name}`,
    "",
    `> ${site.description}`,
    "",
    "## Praxis",
    "",
    `- Name: ${business.legal_name}`,
    `- Adresse: ${formatAddress(business.address)}`,
    `- Telefon: ${business.contact.phone}`,
    `- E-Mail: ${business.contact.email}`,
    ...(business.contact.emergency_phone
      ? [`- Notfallnummer: ${business.contact.emergency_phone}`]
      : []),
    `- Sprachen: ${business.spoken_languages.join(", ")}`,
    `- Kassen: ${business.insurance.join(", ")}`,
    `- Zahlungsarten: ${business.payment_methods.join(", ")}`,
    "",
    "## Sprechzeiten",
    "",
    ...business.opening_hours.map(
      (group) => `- ${formatWeekdays(group.days)}: ${formatSlots(group)}`,
    ),
    ...(hours.appointment_note ? ["", `Hinweis: ${hours.appointment_note}`] : []),
    "",
    "## Leistungen",
    "",
    ...services.map((service) => `- ${service.title}: ${service.summary}`),
    "",
    "## Seiten",
    "",
    ...pages.map((page) => `- [${page.title}](${absoluteUrl(page.path)}): ${page.description}`),
    "",
    "## Fragen und Antworten",
    "",
    ...faq.items.flatMap((item) => [
      `### ${item.question}`,
      "",
      item.answer.join(" "),
      "",
    ]),
    "## Hinweise",
    "",
    ...compliance.medical_disclaimer.map((paragraph) => `- ${paragraph}`),
    `- Diese Website setzt keine Analyse-, Tracking- oder Werbe-Cookies.`,
    `- Stand der Rechtstexte: ${content.legal.imprint.last_updated}.`,
    "",
    `Letzte Aktualisierung der Inhalte: ${content.legal.privacy.last_updated}.`,
    "",
  ];

  return lines.join("\n");
}
