#!/usr/bin/env node
/**
 * Import a reviewed real-client content artifact into the template workspace.
 *
 * This intentionally copies (never transforms) the source JSON and refuses fixture
 * content or incomplete production metadata. The destination pattern is gitignored.
 *
 * Usage:
 *   node scripts/prepare-pilot-content.mjs path/to/client-content.json client-slug
 */
import { access, copyFile, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const templateRoot = path.join(root, "sites", "_template-base");
const [sourceArg, slug] = process.argv.slice(2);
const failures = [];

if (!sourceArg || !slug) {
  console.error("Usage: node scripts/prepare-pilot-content.mjs <source-json> <client-slug>");
  process.exit(2);
}

if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/u.test(slug)) {
  failures.push("client-slug must use lowercase kebab-case");
}

const sourcePath = path.resolve(sourceArg);
let content;
try {
  const raw = await readFile(sourcePath, "utf8");
  content = JSON.parse(raw.replace(/^\uFEFF/u, ""));
} catch (error) {
  failures.push(`source JSON could not be read: ${error.message}`);
}

if (content) {
  if (content?.meta?.is_fixture === true) failures.push("source is marked as a fixture");
  if (content?.compliance?.legal_review_status !== "reviewed") {
    failures.push("source requires compliance.legal_review_status=reviewed");
  }
  if (content?.business?.jurisdiction !== "DE") {
    failures.push("pilot currently requires business.jurisdiction=DE");
  }
  if (!content?.content_schema_version) failures.push("source is missing content_schema_version");
  if (content?.meta?.client_slug && content.meta.client_slug !== slug) {
    failures.push("source meta.client_slug does not match requested client-slug");
  }
}

if (failures.length) {
  console.error("Pilot content preparation failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

const destinationName = `content.real-${slug}.json`;
const destinationPath = path.join(templateRoot, destinationName);
try {
  await access(destinationPath);
  console.error(`Refusing to overwrite existing prepared content: ${destinationName}`);
  process.exit(1);
} catch {}

await copyFile(sourcePath, destinationPath);
console.log(`Prepared reviewed pilot content: ${destinationName}`);
console.log("The destination is intended to remain local/untracked until the pilot is complete.");
