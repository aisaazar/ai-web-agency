import assert from "node:assert/strict";
import { mock, test } from "node:test";

process.env.NEXT_PUBLIC_API_BASE_URL = "http://agency.test";
process.env.AGENCY_ORG_ID = "test-org";

const redirectError = new Error("NEXT_REDIRECT");

mock.module("next/navigation.js", {
  namedExports: { redirect: () => { throw redirectError; } },
});
mock.module("next/headers.js", {
  namedExports: {
    cookies: async () => ({
      get: (name: string) => name === "agency_session" ? { value: "session" } : undefined,
    }),
  },
});

// @ts-expect-error Node's native TypeScript test runner requires the explicit extension.
const { agencyFetch, fetchAuditLog } = await import("./data.ts");

const originalFetch = globalThis.fetch;

test.afterEach(() => {
  globalThis.fetch = originalFetch;
});

test("agencyFetch redirects on 401", async () => {
  globalThis.fetch = async () => new Response("", { status: 401 });

  await assert.rejects(
    () => agencyFetch("/v1/dashboard/overview"),
    (error: unknown) => error === redirectError,
  );
});

test("agencyFetch throws a diagnosable error when the API is unreachable", async () => {
  globalThis.fetch = async () => { throw new Error("ECONNREFUSED"); };

  await assert.rejects(
    () => agencyFetch("/v1/dashboard/overview"),
    (error: unknown) =>
      error instanceof Error &&
      error.message.includes("Agency API request failed") &&
      error.message.includes("unreachable") &&
      error.message.includes("/v1/dashboard/overview") &&
      error.message.includes("ECONNREFUSED"),
  );
});

test("agencyFetch throws status and endpoint details on 5xx", async () => {
  globalThis.fetch = async () => new Response("upstream exploded", { status: 503 });

  await assert.rejects(
    () => agencyFetch("/v1/dashboard/overview"),
    (error: unknown) =>
      error instanceof Error &&
      error.message.includes("status 503") &&
      error.message.includes("/v1/dashboard/overview") &&
      error.message.includes("upstream exploded"),
  );
});

test("fetchAuditLog returns an empty list for owner-only 403", async () => {
  let requested = "";
  globalThis.fetch = async (input) => {
    requested = String(input);
    return new Response("", { status: 403 });
  };

  assert.deepEqual(await fetchAuditLog(), []);
  assert.match(requested, /\/v1\/audit\?org_id=test-org&limit=50$/);
});
