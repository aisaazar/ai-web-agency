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

// Dashboard server components read the agency API through one helper. Without it each call site
// throws Next's raw "fetch failed" on an outage, which `app/error.tsx` cannot recognise as an API
// problem, and an operator sees "Dashboard error" instead of "Agency API unavailable".
const dataLib = readFileSync(join(root, "apps", "dashboard", "src", "lib", "data.ts"), "utf8");
if (!dataLib.includes("async function agencyFetch(")) {
  throw new Error("dashboard API access regression: lib/data.ts must centralize API calls in agencyFetch");
}
// Every API the dashboard reads must still be addressed, and each read must go through the helper.
// Call sites build their path differently (inline template, quoted literal, hoisted variable), so
// this asserts the endpoint is requested at all plus a usage count, not string adjacency.
for (const endpoint of [
  "/v1/dashboard/overview",
  "/v1/dashboard/clients/",
  "/v1/dashboard/llm-cost",
  "/v1/deploys/logs",
]) {
  if (!dataLib.includes(endpoint)) {
    throw new Error(`dashboard API access regression: ${endpoint} is no longer requested`);
  }
}
const agencyFetchCalls = (dataLib.match(/agencyFetch\(/g) ?? []).length;
// One definition plus one call per read endpoint.
if (agencyFetchCalls < 5) {
  throw new Error(
    `dashboard API access regression: only ${agencyFetchCalls} agencyFetch usages; every API read must use it`,
  );
}
// /v1/audit deliberately probes the raw response first so a non-owner's 403 can become an empty
// state instead of an error boundary; enforce that exception rather than weakening the helper.
const auditStart = dataLib.indexOf("const auditPath =");
const auditEnd = dataLib.indexOf("\n\n  const data = await response.json()", auditStart);
const auditBlock = dataLib.slice(auditStart, auditEnd);
if (!auditBlock.includes("probe = await fetch(") || !auditBlock.includes("probe?.status === 403")) {
  throw new Error("dashboard audit authorization regression: /v1/audit must preserve the explicit 403 probe");
}
// The error boundary must still distinguish an API outage from a bug in the view.
const errorBoundary = readFileSync(join(root, "apps", "dashboard", "src", "app", "error.tsx"), "utf8");
for (const fragment of ["Agency API unavailable", "API_FAILURE"]) {
  if (!errorBoundary.includes(fragment)) {
    throw new Error("dashboard error boundary regression: missing " + fragment);
  }
}

const prospectsPage = readFileSync(join(root, "apps", "dashboard", "src", "app", "prospects", "page.tsx"), "utf8");
for (const fragment of ['action={"/api/prospects/" + p.id + "/status"}', 'name="status"', 'name="note"']) {
  if (!prospectsPage.includes(fragment)) {
    throw new Error("prospect workflow regression: missing " + fragment);
  }
}
const prospectStatusRoute = readFileSync(
  join(root, "apps", "dashboard", "src", "app", "api", "prospects", "[prospectId]", "status", "route.ts"),
  "utf8",
);
for (const fragment of ['method: "PATCH"', '"X-CSRF-Token": csrf', 'org_id=', "API%20is%20currently%20unavailable"]) {
  if (!prospectStatusRoute.includes(fragment)) {
    throw new Error("prospect status security regression: missing " + fragment);
  }
}

console.log("dashboard-csrf-check: PASS");
