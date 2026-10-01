#!/usr/bin/env node
/**
 * Real-client pilot preflight. This is intentionally stricter than development gates and
 * never prints secret values. It checks only the release inputs needed for a customer rehearsal.
 *
 * Usage:
 *   CONTENT_FILE=content.real-client.json node scripts/pilot-preflight.mjs
 *
 * On Windows PowerShell:
 *   $env:CONTENT_FILE="content.real-client.json"; node scripts/pilot-preflight.mjs
 */
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const templateRoot = path.join(root, "sites", "_template-base");
const contentName = (process.env.CONTENT_FILE || "").trim();
const failures = [];

function required(name) {
  if (!(process.env[name] || "").trim()) failures.push(`${name} is required`);
  return (process.env[name] || "").trim();
}

if ((process.env.AGENCY_ENV || "").trim().toLowerCase() !== "production") {
  failures.push("AGENCY_ENV=production is required for pilot preflight");
}
for (const [name, expected] of [
  ["AGENCY_RESEARCH_PROVIDER", "tavily"],
  ["AGENCY_LLM_PROVIDER", "local"],
  ["AGENCY_NOTIFY_PROVIDER", "smtp"],
  ["AGENCY_DEPLOY_PROVIDER", "vercel"],
]) {
  const actual = (process.env[name] || "").trim().toLowerCase();
  if (actual !== expected) failures.push(`${name}=${expected} is required (got ${actual || "missing"})`);
}

const leadApi = required("NEXT_PUBLIC_AGENCY_LEAD_API_URL");
const siteId = required("NEXT_PUBLIC_AGENCY_SITE_ID");
required("NEXT_PUBLIC_TURNSTILE_SITE_KEY");
if (leadApi) {
  try {
    const url = new URL(leadApi);
    if (url.protocol !== "https:") failures.push("NEXT_PUBLIC_AGENCY_LEAD_API_URL must use HTTPS");
    if (url.username || url.password) failures.push("NEXT_PUBLIC_AGENCY_LEAD_API_URL must not contain credentials");
  } catch {
    failures.push("NEXT_PUBLIC_AGENCY_LEAD_API_URL is not a valid URL");
  }
}

if (!contentName) {
  failures.push("CONTENT_FILE is required for a real-client pilot");
} else if (path.basename(contentName) !== contentName || !contentName.endsWith(".json")) {
  failures.push("CONTENT_FILE must be a JSON filename inside sites/_template-base");
} else {
  const contentPath = path.join(templateRoot, contentName);
  try {
    const content = JSON.parse(await readFile(contentPath, "utf8"));
    if (content?.meta?.is_fixture === true) failures.push("CONTENT_FILE is still marked as fixture");
    if (content?.compliance?.legal_review_status !== "reviewed") failures.push("CONTENT_FILE requires legal_review_status=reviewed");
    if (content?.business?.jurisdiction !== "DE") failures.push("pilot template currently requires business.jurisdiction=DE");
    if (!content?.content_schema_version) failures.push("CONTENT_FILE is missing content_schema_version");
  } catch (error) {
    failures.push(`CONTENT_FILE could not be read: ${error.message}`);
  }
}

if (failures.length) {
  console.error("Pilot preflight failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

const runtime = spawnSync(process.execPath, [path.join(root, "scripts", "validate-production-config.mjs")], {
  cwd: root,
  env: process.env,
  stdio: "inherit",
});
if (runtime.status !== 0) process.exit(runtime.status ?? 1);

console.log(`Pilot preflight passed: production posture, reviewed client content, and public deployment config are ready for ${siteId}.`);
