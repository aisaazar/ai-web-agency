#!/usr/bin/env node
/**
 * Build and QA a private sales demo from an existing prospect artifact.
 *
 * The output is deliberately isolated under .artifacts and never becomes a production build.
 * Usage: npm run sales:demo:wittmann
 */
import { access, cp, mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const templateRoot = path.join(root, "sites", "_template-base");
const demoRoot = path.join(root, ".artifacts", "sales-demo-wittmann");
const contentSource = path.join(demoRoot, "content.demo.json");
const tempContentName = "content.generated.sales-demo-wittmann.json";
const tempContent = path.join(templateRoot, tempContentName);
const outputRoot = path.join(demoRoot, "site");
const npmCli = path.join(path.dirname(process.execPath), "node_modules", "npm", "bin", "npm-cli.js");

function run(command, args, env = {}) {
  const result = spawnSync(command, args, {
    cwd: root,
    env: { ...process.env, ...env },
    stdio: "inherit",
    shell: false,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

await mkdir(demoRoot, { recursive: true });
// Rebuild the prospect artifact from the tracked, reviewable generator so the demo is reproducible.
run(process.execPath, ["scripts/build-wittmann-demo.mjs"]);
await access(contentSource);

await rm(tempContent, { force: true });
await cp(contentSource, tempContent);

try {
  // DEVELOPMENT build only: the artifact remains explicitly marked as a private fixture.
  // That is intentional; a sales concept must never satisfy the production gate.
  run(process.execPath, [npmCli, "run", "build:site"], {
    CONTENT_FILE: tempContentName,
    DESIGN_PRESET_ID: "health",
    PRODUCTION_BUILD: "0",
  });

  await rm(outputRoot, { recursive: true, force: true });
  await cp(path.join(templateRoot, "out"), outputRoot, { recursive: true });

  const outputEnv = {
    OUTPUT_DIR: outputRoot,
    OUTPUT_MARKERS: "Mundgesundheit Schwabach,Leistungen,Impressum",
    SMOKE_OUT_DIR: outputRoot,
  };
  run(process.execPath, ["sites/_template-base/scripts/validate-output.mjs"], outputEnv);
  run(process.execPath, ["scripts/site-smoke.mjs"], outputEnv);

  const summary = [
    "# Wittmann Sales Demo",
    "",
    "Private redesign concept — not an authorized client website.",
    "",
    "Output: " + path.relative(root, outputRoot),
    "",
    "Suggested presentation flow:",
    "1. Start on the homepage and show the local identity + appointment CTA.",
    "2. Open Leistungen to show the information hierarchy.",
    "3. Resize to mobile and show the compact navigation and contact path.",
    "4. Explain that the same production template can be branded and populated after approval.",
    "",
    "Do not publish this artifact, attach the prospect domain, or represent the prospect as a client.",
    "",
  ].join("\n");
  await writeFile(path.join(demoRoot, "SALES-DEMO.md"), summary, "utf8");
  console.log("Sales demo ready: " + path.relative(root, outputRoot));
} finally {
  await rm(tempContent, { force: true });
}
