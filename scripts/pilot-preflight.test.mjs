import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { mkdtempSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const script = path.join(root, "scripts", "pilot-preflight.mjs");
const templateDir = path.join(root, "sites", "_template-base");

function run(env) {
  try {
    execFileSync(process.execPath, [script], {
      cwd: root,
      env: { ...process.env, ...env },
      stdio: "pipe",
      encoding: "utf8",
    });
    return 0;
  } catch (error) {
    return error.status ?? 1;
  }
}

function base() {
  return {
    AGENCY_ENV: "production",
    AGENCY_DATABASE_URL: "postgresql://db.example/agency",
    AGENCY_ALLOWED_ORIGINS: "https://client.example",
    AGENCY_COOKIE_SECURE: "true",
    AGENCY_TURNSTILE_SECRET: "synthetic",
    AGENCY_RESEARCH_PROVIDER: "tavily",
    AGENCY_LLM_PROVIDER: "local",
    AGENCY_NOTIFY_PROVIDER: "smtp",
    AGENCY_DEPLOY_PROVIDER: "vercel",
    VERCEL_PROJECT_ID: "prj_synthetic",
    VERCEL_TOKEN: "synthetic",
    NEXT_PUBLIC_AGENCY_LEAD_API_URL: "https://api.client.example",
    NEXT_PUBLIC_AGENCY_SITE_ID: "site-synthetic",
    NEXT_PUBLIC_TURNSTILE_SITE_KEY: "1x00000000000000000000AA",
  };
}

test("pilot preflight rejects fixture content", () => {
  assert.equal(run({ ...base(), CONTENT_FILE: "content.dental-clinic.json" }), 1);
});

test("pilot preflight accepts reviewed non-fixture content", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "ai-web-pilot-"));
  const name = `pilot-${path.basename(dir)}.json`;
  const target = path.join(templateDir, name);
  const fixture = JSON.parse(readFileSync(path.join(templateDir, "content.dental-clinic.json"), "utf8"));
  fixture.meta.is_fixture = false;
  fixture.compliance.legal_review_status = "reviewed";
  writeFileSync(target, JSON.stringify(fixture), "utf8");
  try {
    assert.equal(run({ ...base(), CONTENT_FILE: name }), 0);
  } finally {
    unlinkSync(target);
  }
});
