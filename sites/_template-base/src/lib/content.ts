/**
 * The one place where the content artifact enters the application.
 * The source JSON is selected at build time so one template can build many clients.
 */
import fs from "node:fs";
import path from "node:path";

import type { ContentModel, PageSeo } from "@ai-web-agency/contracts";

import {
  CONTENT_FILE,
  PRODUCTION_BUILD,
  REQUIRED_PAGE_PATHS,
  SUPPORTED_CONTENT_SCHEMA_VERSIONS,
  isSupportedContentSchemaVersion,
} from "../../template.config";

const contentPath = path.resolve(process.cwd(), CONTENT_FILE);
if (!fs.existsSync(contentPath)) {
  throw new Error(`Content artifact not found: ${CONTENT_FILE}`);
}

const parsed = JSON.parse(fs.readFileSync(contentPath, "utf8")) as ContentModel;
if (!isSupportedContentSchemaVersion(parsed.content_schema_version)) {
  throw new Error(
    `Content artifact ${CONTENT_FILE} declares schema version ${parsed.content_schema_version}, ` +
      `but this template supports [${SUPPORTED_CONTENT_SCHEMA_VERSIONS.join(", ")}] (ADR-006).`,
  );
}

for (const requiredPath of REQUIRED_PAGE_PATHS) {
  if (!parsed.seo.pages.some((page) => page.path === requiredPath)) {
    throw new Error(
      `Content artifact ${CONTENT_FILE} has no seo.pages entry for ${requiredPath}. ` +
        "A German site cannot be published without Impressum and Datenschutz (ADR-014).",
    );
  }
}

if (PRODUCTION_BUILD && parsed.meta.is_fixture) {
  throw new Error(
    `PRODUCTION_BUILD=1 but ${CONTENT_FILE} is fixture content (meta.is_fixture = true). ` +
      "Fixture content never reaches a client domain (docs/PIPELINE-AND-GATE.md).",
  );
}

export const content: ContentModel = parsed;
export const origin: string = String(content.site.url).replace(/\/+$/, "");
export const isFixtureBuild: boolean = content.meta.is_fixture;

export function pageSeo(pathname: string): PageSeo {
  const page = content.seo.pages.find((candidate) => candidate.path === pathname);
  if (!page) throw new Error(`No seo.pages entry for ${pathname} - add it to the content artifact first.`);
  return page;
}

export function absoluteUrl(pathname: string): string {
  return `${origin}${pathname}`;
}
