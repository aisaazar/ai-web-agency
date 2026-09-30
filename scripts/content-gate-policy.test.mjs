import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";

/**
 * Regression coverage for the two production-only content-gate policies.
 *
 * `fixture_policy` and `legal_review_policy` are the reason the reference fixture
 * (`sites/_template-base/content.dental-clinic.json`) can never be shipped to a client:
 * the release E2E has to build a *client-posture* artifact, so without these tests a
 * change that quietly flipped the production flag would look like a passing suite while
 * the last line of defence against publishing fixture or legally unreviewed text was gone.
 */
const gate = fileURLToPath(new URL("../sites/_template-base/scripts/gate/validate-content.mjs", import.meta.url));
const fixturePath = fileURLToPath(new URL("../sites/_template-base/content.dental-clinic.json", import.meta.url));

/** Public build configuration a real client build receives; none of it is a secret. */
const PRODUCTION_ENV = {
  PRODUCTION_BUILD: "1",
  NEXT_PUBLIC_AGENCY_LEAD_API_URL: "https://e2e-api.example.test",
  NEXT_PUBLIC_TURNSTILE_SITE_KEY: "1x00000000000000000000AA",
  NEXT_PUBLIC_AGENCY_SITE_ID: "11111111-1111-1111-1111-111111111111",
  NEXT_PUBLIC_AGENCY_CLIENT_ID: "22222222-2222-2222-2222-222222222222",
};

function runGate(env, production = true) {
  const contentFile = env.CONTENT_FILE;
  try {
    const args = production ? [gate, "--production"] : [gate];
    const stdout = execFileSync(process.execPath, args, {
      env: { ...process.env, ...env },
      encoding: "utf8",
      stdio: "pipe",
    });
    return { status: 0, output: stdout };
  } catch (error) {
    assert.ok(
      contentFile === undefined || error.status !== undefined,
      `content gate crashed on ${contentFile}`,
    );
    return { status: error.status ?? 1, output: `${error.stdout ?? ""}${error.stderr ?? ""}` };
  }
}

const failedChecks = (output) =>
  output
    .split(/\r?\n/)
    .filter((line) => line.startsWith("[FAIL]"))
    .map((line) => line.slice("[FAIL]".length).split(" - ")[0].trim());

/** A copy of the fixture in the posture a real, legally reviewed client artifact has. */
function writeClientArtifact() {
  const content = JSON.parse(readFileSync(fixturePath, "utf8"));
  content.meta.is_fixture = false;
  content.compliance.legal_review_status = "reviewed";
  const destination = path.join(
    mkdtempSync(path.join(tmpdir(), "agency-gate-")),
    "content.client.json",
  );
  writeFileSync(destination, `${JSON.stringify(content, null, 2)}\n`, "utf8");
  return destination;
}

test("the tracked reference fixture still declares itself fixture and unreviewed", () => {
  const content = JSON.parse(readFileSync(fixturePath, "utf8"));
  assert.equal(content.meta.is_fixture, true);
  assert.equal(content.compliance.legal_review_status, "pending");
});

test("production gate refuses the reference fixture", () => {
  const { status, output } = runGate({ ...PRODUCTION_ENV, CONTENT_FILE: fixturePath });
  assert.equal(status, 1);
  assert.deepEqual(failedChecks(output).sort(), ["fixture_policy", "legal_review_policy"]);
});

test("production gate accepts a reviewed client artifact built from the same template", () => {
  const { status, output } = runGate({ ...PRODUCTION_ENV, CONTENT_FILE: writeClientArtifact() });
  assert.equal(status, 0, output);
});

test("development gate keeps the reference fixture buildable", () => {
  const { status, output } = runGate({
    ...PRODUCTION_ENV,
    PRODUCTION_BUILD: "0",
    CONTENT_FILE: fixturePath,
  }, false);
  assert.equal(status, 0, output);
  assert.equal(failedChecks(output).length, 0);
});
