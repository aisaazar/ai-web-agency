import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";
import assert from "node:assert/strict";

const script = fileURLToPath(new URL("./validate-production-config.mjs", import.meta.url));
const run = (env) => {
  try {
    execFileSync(process.execPath, [script], {
      env: { ...process.env, ...env },
      stdio: "pipe",
      encoding: "utf8",
    });
    return 0;
  } catch (error) {
    return error.status ?? 1;
  }
};

test("production preflight fails closed when required runtime config is absent", () => {
  const code = run({
    AGENCY_ENV: "",
    AGENCY_ALLOWED_ORIGINS: "",
    AGENCY_COOKIE_SECURE: "",
    AGENCY_TURNSTILE_SECRET: "",
    AGENCY_DEPLOY_PROVIDER: "",
    VERCEL_PROJECT_ID: "",
    VERCEL_TOKEN: "",
  });
  assert.equal(code, 1);
});

test("production preflight accepts structurally valid synthetic Vercel config", () => {
  const code = run({
    AGENCY_ENV: "production",
    AGENCY_ALLOWED_ORIGINS: "https://client.example",
    AGENCY_COOKIE_SECURE: "true",
    AGENCY_TURNSTILE_SECRET: "synthetic",
    AGENCY_DEPLOY_PROVIDER: "vercel",
    VERCEL_PROJECT_ID: "prj_synthetic",
    VERCEL_TOKEN: "synthetic",
  });
  assert.equal(code, 0);
});

test("production preflight rejects insecure origins", () => {
  const code = run({
    AGENCY_ENV: "production",
    AGENCY_ALLOWED_ORIGINS: "http://client.example",
    AGENCY_COOKIE_SECURE: "true",
    AGENCY_TURNSTILE_SECRET: "synthetic",
    AGENCY_DEPLOY_PROVIDER: "local_static",
  });
  assert.equal(code, 1);
});
