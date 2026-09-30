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

console.log("dashboard-csrf-check: PASS");
