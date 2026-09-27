#!/usr/bin/env node
/**
 * Content gate — the checks `docs/PIPELINE-AND-GATE.md` §2 requires before a build:
 *
 *   content_schema         Ajv (JSON Schema 2020-12) against packages/contracts/content.schema.json
 *   content_schema_version ADR-005/ADR-006: the artifact version must be one this template supports
 *   required_legal_pages   ADR-014: Impressum + Datenschutz for the declared jurisdiction (DE)
 *   claims_policy          banned medical/legal/superlative claim scan (DE + EN)
 *   url_policy             no third-party runtime dependency, no http://, no URL in a text field
 *   language_policy        formal German address ("Sie"), never "du/dein/euch"
 *   preset_policy          the declared design preset exists and is well formed
 *   fixture_policy         fixture content can never reach a production build
 *
 * The JSON Schema is generated (Pydantic -> JSON Schema, ADR-004) and never hand-edited.
 *
 * Usage:
 *   node scripts/gate/validate-content.mjs                # development/fixture mode
 *   node scripts/gate/validate-content.mjs --production    # fixture content becomes fatal
 */
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";

import {
  contentLabel,
  contentPath,
  createReport,
  designPresetLabel,
  readContent,
  readContentSchema,
  readDesignPreset,
  templateConfig,
} from "../lib/paths.mjs";

void contentPath;

/** Banned claims for a German dental practice (docs/SECURITY-AND-RISKS.md: claim risk is legal). */
const BANNED_CLAIM_PATTERNS = [
  { pattern: /\bgarantiert\w*\b/iu, reason: "guarantee claim" },
  { pattern: /\bgarantie\w*\b/iu, reason: "guarantee claim" },
  { pattern: /\b100\s?%/u, reason: "absolute claim" },
  { pattern: /\bschmerzfrei\w*\b/iu, reason: "medical outcome promise" },
  { pattern: /\bschmerzlos\w*\b/iu, reason: "medical outcome promise" },
  { pattern: /\brisikofrei\w*\b/iu, reason: "risk-free claim" },
  { pattern: /\bohne\s+Risiko\b/iu, reason: "risk-free claim" },
  { pattern: /\bNr\.?\s?1\b/u, reason: "ranking claim" },
  { pattern: /\bNummer\s+1\b/iu, reason: "ranking claim" },
  { pattern: /\bweltbest\w*\b/iu, reason: "superlative" },
  { pattern: /\bführend\w*\b/iu, reason: "superlative" },
  { pattern: /\bheilt\b/iu, reason: "medical cure claim" },
  { pattern: /\bWunderheilung\b/iu, reason: "medical cure claim" },
  { pattern: /\bpreiswerteste\w*\b/iu, reason: "price superlative" },
  { pattern: /\b(?:guaranteed|pain-?free|no-?risk)\b/iu, reason: "English banned claim" },
];

/** Third-party hosts are both a DSGVO problem and a runtime dependency. */
const FORBIDDEN_HOSTS = [
  "fonts.googleapis.com",
  "fonts.gstatic.com",
  "gstatic.com",
  "googleapis.com",
  "use.typekit.net",
  "cdn.jsdelivr.net",
  "unpkg.com",
  "cdnjs.cloudflare.com",
  "googletagmanager.com",
  "google-analytics.com",
  "doubleclick.net",
  "connect.facebook.net",
  "hotjar.com",
  "youtube.com/embed",
  "vimeo.com/video",
];

/** Only these field names may carry an absolute URL (click-through links, never embeds). */
const EXTERNAL_URL_FIELDS = new Set(["url", "link_url"]);

/** Informal German address. The product writes "Sie" (docs/PLAN-14-DAYS.md, Day 6). */
const INFORMAL_GERMAN_PATTERN =
  /\b(du|dich|dir|dein|deine|deinem|deinen|deiner|deines|euch|euer|eure|eurem|euren|eurer)\b/iu;

/** Depth-first walk yielding every string of the artifact with its JSON path. */
function walkStrings(node, currentPath, visit) {
  if (typeof node === "string") {
    visit(node, currentPath);
    return;
  }
  if (Array.isArray(node)) {
    node.forEach((entry, index) => walkStrings(entry, [...currentPath, String(index)], visit));
    return;
  }
  if (node && typeof node === "object") {
    for (const [key, value] of Object.entries(node)) {
      walkStrings(value, [...currentPath, key], visit);
    }
  }
}

const formatPath = (segments) => segments.join(".");

const report = createReport("content gate");
const production = process.argv.includes("--production") || process.env.PRODUCTION_BUILD === "1";

let content;
try {
  content = readContent();
} catch (error) {
  console.error(`cannot read ${contentLabel}: ${error.message}`);
  process.exit(1);
}

// 1. content_schema ------------------------------------------------------------------------------
const ajv = new Ajv2020({ allErrors: true, strict: false });
addFormats(ajv);
const schema = readContentSchema();
const validate = ajv.compile(schema);
const valid = validate(content);
report.check(
  "content_schema",
  valid,
  valid ? String(schema.$id) : `${validate.errors?.length ?? 0} Ajv error(s) in ${contentLabel}`,
);
if (!valid) {
  for (const error of (validate.errors ?? []).slice(0, 20)) {
    console.error(`  ${error.instancePath || "/"} ${error.message ?? "(no message)"}`);
  }
}

// 2. content_schema_version (ADR-005 / ADR-006) ---------------------------------------------------
const version = content?.content_schema_version;
const supported = templateConfig.supported_content_schema_versions;
report.check(
  "content_schema_version",
  typeof version === "string" && supported.includes(version),
  supported.includes(version)
    ? `${version} supported`
    : `${version ?? "missing"} not in [${supported.join(", ")}]`,
);

// 3. required_legal_pages (ADR-014) --------------------------------------------------------------
const pagePaths = Array.isArray(content?.seo?.pages) ? content.seo.pages.map((p) => p.path) : [];
const missingPaths = templateConfig.required_page_paths.filter((p) => !pagePaths.includes(p));
const duplicatePaths = pagePaths.filter((p, index) => pagePaths.indexOf(p) !== index);
const jurisdiction = content?.business?.jurisdiction;
report.check(
  "required_legal_pages",
  missingPaths.length === 0 &&
    duplicatePaths.length === 0 &&
    Boolean(content?.legal?.imprint) &&
    Boolean(content?.legal?.privacy) &&
    jurisdiction === "DE",
  missingPaths.length > 0
    ? `missing seo.pages entry for ${missingPaths.join(", ")}`
    : duplicatePaths.length > 0
      ? `duplicate seo.pages entry: ${duplicatePaths.join(", ")}`
      : `jurisdiction ${jurisdiction}, Impressum + Datenschutz present`,
);

// 4. claims_policy -------------------------------------------------------------------------------
const claimHits = [];
walkStrings(content, [], (value, at) => {
  for (const rule of BANNED_CLAIM_PATTERNS) {
    if (rule.pattern.test(value)) {
      claimHits.push(`${formatPath(at)}: "${value.slice(0, 60)}" (${rule.reason})`);
    }
  }
});
report.check("claims_policy", claimHits.length === 0, `${claimHits.length} hit(s)`);
for (const hit of claimHits.slice(0, 10)) {
  console.error(`  ${hit}`);
}

// 5. url_policy ----------------------------------------------------------------------------------
const urlViolations = [];
walkStrings(content, [], (value, at) => {
  const lastSegment = at[at.length - 1] ?? "";
  const lower = value.toLowerCase();
  for (const host of FORBIDDEN_HOSTS) {
    if (lower.includes(host)) {
      urlViolations.push(`${formatPath(at)}: forbidden third-party host ${host}`);
    }
  }
  if (lower.includes("http://")) {
    urlViolations.push(`${formatPath(at)}: insecure http:// URL`);
  }
  const hasScheme = lower.includes("://");
  if (hasScheme && !EXTERNAL_URL_FIELDS.has(lastSegment)) {
    urlViolations.push(`${formatPath(at)}: absolute URL in a non-URL field`);
  }
  if (hasScheme && EXTERNAL_URL_FIELDS.has(lastSegment) && !lower.startsWith("https://")) {
    urlViolations.push(`${formatPath(at)}: URL must be absolute https`);
  }
});
report.check("url_policy", urlViolations.length === 0, `${urlViolations.length} violation(s)`);
for (const violation of urlViolations.slice(0, 10)) {
  console.error(`  ${violation}`);
}

// 6. language_policy -----------------------------------------------------------------------------
const informalHits = [];
walkStrings(content, [], (value, at) => {
  if (INFORMAL_GERMAN_PATTERN.test(value)) {
    informalHits.push(`${formatPath(at)}: "${value.slice(0, 60)}"`);
  }
});
report.check(
  "language_policy",
  informalHits.length === 0,
  informalHits.length === 0 ? "formal German (Sie)" : `${informalHits.length} informal hit(s)`,
);
for (const hit of informalHits.slice(0, 10)) {
  console.error(`  ${hit}`);
}

// 7. preset_policy -------------------------------------------------------------------------------
let presetOk = false;
let presetDetail = designPresetLabel;
try {
  const preset = readDesignPreset();
  presetOk =
    Boolean(preset?.id) && Boolean(preset?.tokens?.colors) && Boolean(preset?.tokens?.fonts?.sans);
  presetDetail = `${designPresetLabel} (id: ${preset?.id})`;
} catch (error) {
  presetDetail = `${designPresetLabel} unreadable: ${error.message}`;
}
report.check("preset_policy", presetOk, presetDetail);

// 8. fixture_policy + legal_review_policy --------------------------------------------------------
const isFixture = content?.meta?.is_fixture === true;
const reviewStatus = content?.compliance?.legal_review_status;
if (production) {
  report.check(
    "fixture_policy",
    !isFixture,
    isFixture ? "fixture content cannot be published (meta.is_fixture = true)" : "client content",
  );
  report.check(
    "legal_review_policy",
    reviewStatus === "reviewed",
    `legal_review_status = ${reviewStatus}`,
  );
} else if (isFixture) {
  report.note(
    "fixture_policy",
    "meta.is_fixture = true - allowed in development, fatal with --production",
  );
  if (reviewStatus !== "reviewed") {
    report.note("legal_review_policy", `legal_review_status = ${reviewStatus} (fixture)`);
  }
}

if (production) {
  const leadApi = process.env.NEXT_PUBLIC_AGENCY_LEAD_API_URL?.trim() ?? "";
  const siteId = process.env.NEXT_PUBLIC_AGENCY_SITE_ID?.trim() ?? "";
  const agentApi = process.env.NEXT_PUBLIC_AGENCY_AGENT_API_URL?.trim() ?? "";
  const publicApiUrls = [
    ["NEXT_PUBLIC_AGENCY_LEAD_API_URL", leadApi, true],
    ["NEXT_PUBLIC_AGENCY_AGENT_API_URL", agentApi, false],
  ];
  const urlProblems = [];
  for (const [name, value, required] of publicApiUrls) {
    if (!value) {
      if (required) urlProblems.push(`${name} is required`);
      continue;
    }
    try {
      const url = new URL(value);
      if (url.protocol !== "https:") urlProblems.push(`${name} must use HTTPS`);
      if (url.username || url.password) urlProblems.push(`${name} must not contain credentials`);
    } catch {
      urlProblems.push(`${name} is not a valid URL`);
    }
  }
  report.check(
    "production_config",
    Boolean(siteId) && urlProblems.length === 0,
    Boolean(siteId) && urlProblems.length === 0
      ? "lead API, site ID, and optional agent API are production-safe"
      : [siteId ? "" : "NEXT_PUBLIC_AGENCY_SITE_ID is required", ...urlProblems].filter(Boolean).join("; "),
  );
}

// 9. deterministic_manifest ----------------------------------------------------------------------
report.check(
  "deterministic_manifest",
  typeof content?.legal?.imprint?.last_updated === "string" &&
    typeof content?.legal?.privacy?.last_updated === "string",
  "legal last_updated is content-provided; sitemap/robots/llms.txt derive from content only",
);

process.exit(report.finish());

