import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const source = readFileSync(
  join(root, "apps", "dashboard", "src", "lib", "data.ts"),
  "utf8",
);
const start = source.indexOf("export async function fetchDeploymentLogs");
const end = source.indexOf("\n}\n", start) + 3;
if (start < 0 || end < 3) throw new Error("fetchDeploymentLogs was not found");

const block = source.slice(start, end);
const required = [
  'cookieStore.get("agency_csrf")?.value',
  '"X-CSRF-Token": csrfCookie',
  'agency_csrf=" + csrfCookie',
];

for (const fragment of required) {
  if (!block.includes(fragment)) {
    throw new Error("Deployment logs CSRF regression: missing " + fragment);
  }
}

const clientPage = readFileSync(
  join(root, "apps", "dashboard", "src", "app", "clients", "[clientId]", "page.tsx"),
  "utf8",
);
const failedRetry = [
  'case "FAILED":',
  'action="generate-content"',
  "Retry failed content generation",
];
for (const fragment of failedRetry) {
  if (!clientPage.includes(fragment)) {
    throw new Error("FAILED pipeline recovery regression: missing " + fragment);
  }
}

const actionRoute = readFileSync(
  join(root, "apps", "dashboard", "src", "app", "api", "clients", "[clientId]", "action", "route.ts"),
  "utf8",
);
for (const fragment of [
  'const LLM_PROVIDER = process.env.AGENCY_LLM_PROVIDER?.trim() || "mock";',
  'provider: String(form.get("provider") ?? LLM_PROVIDER)',
]) {
  if (!actionRoute.includes(fragment)) {
    throw new Error("provider default regression: missing " + fragment);
  }
}

for (const fragment of [
  'case "design": {',
  "isDesignPresetId(presetId)",
  "preset_id: presetId",
]) {
  if (!actionRoute.includes(fragment)) {
    throw new Error("design preset forwarding regression: missing " + fragment);
  }
}

// The action route must validate against the shared catalog rather than a second hardcoded copy
// of the preset list, which is what used to let intake and design disagree.
if (!/from\s+["'][^"']*lib\/design-presets["']/.test(actionRoute)) {
  throw new Error("design preset validation regression: action route must use the shared catalog");
}

for (const fragment of ['name="preset_id"', "Design preset", "DESIGN_PRESET_LABELS"]) {
  if (!clientPage.includes(fragment)) {
    throw new Error("design preset selector regression: missing " + fragment);
  }
}

// The catalog is the single source of truth for which presets exist and how they are labelled.
const presetLib = readFileSync(
  join(root, "apps", "dashboard", "src", "lib", "design-presets.ts"),
  "utf8",
);
for (const fragment of ["DESIGN_PRESETS", "DESIGN_PRESET_LABELS", "health", "corporate", "warm"]) {
  if (!presetLib.includes(fragment)) {
    throw new Error("design preset catalog regression: missing " + fragment);
  }
}

console.log("dashboard-csrf-check: PASS");
