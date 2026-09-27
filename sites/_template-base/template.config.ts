/**
 * The TypeScript view of `template.config.json`. The JSON manifest is the single declared source of
 * truth (it is what the Node gates and the build service read); this module only re-exports it in a
 * typed form so no constant can drift between the app and the gates.
 */
import templateConfig from "./template.config.json";

/**
 * ADR-006 / ADR-005: unsupported artifact schema versions fail loudly.
 */
export const SUPPORTED_CONTENT_SCHEMA_VERSIONS: readonly string[] =
  templateConfig.supported_content_schema_versions;

/** Build-time selected client artifact; defaults to the reference fixture. */
export const CONTENT_FILE =
  process.env.CONTENT_FILE?.trim() || templateConfig.content_file;

/** ADR-014: a German site is unpublishable without these. */
export const REQUIRED_PAGE_PATHS: readonly string[] = templateConfig.required_page_paths;

export function isSupportedContentSchemaVersion(version: string): boolean {
  return SUPPORTED_CONTENT_SCHEMA_VERSIONS.includes(version);
}

/**
 * Explicit production gate. Development/fixture builds run with plain `npm run build`.
 */
export const PRODUCTION_BUILD: boolean = process.env.PRODUCTION_BUILD === "1";
