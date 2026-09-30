import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const nodeBin = path.dirname(process.execPath);
const env = {
  ...process.env,
  AGENCY_NPM_COMMAND: path.join(nodeBin, "npm.cmd"),
  NEXT_PUBLIC_AGENCY_LEAD_API_URL: "https://e2e-api.example.test",
  NEXT_PUBLIC_TURNSTILE_SITE_KEY: "1x00000000000000000000AA",
  NEXT_PUBLIC_AGENCY_CLIENT_ID: "e2e-test-client",
  RUN_REAL_E2E: "1",
};
const currentPath = env.PATH || env.Path || "";
for (const key of Object.keys(env)) {
  if (key.toUpperCase() === "PATH") delete env[key];
}
env.PATH = [nodeBin, currentPath].filter(Boolean).join(path.delimiter);
const result = spawnSync(
  process.execPath,
  [path.join(root, "scripts", "py.mjs"), "-m", "pytest", "apps/api/tests/test_end_to_end_lifecycle.py", "-q"],
  { cwd: root, env, stdio: "inherit" },
);
if (result.error) throw result.error;
process.exit(result.status ?? 1);
