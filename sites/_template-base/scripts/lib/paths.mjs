#!/usr/bin/env node
/**
 * Shared paths and reporting for the template's Node gates.
 *
 * The gates run *before* (`scripts/gate/validate-content.mjs`) and *after*
 * (`scripts/validate-output.mjs`) the static build, mirroring
 * `docs/PIPELINE-AND-GATE.md` §2. Nothing here duplicates app code: the gates consume the same
 * generated contract and the same content artifact the app does.
 */
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);

/** `<repo>/sites/_template-base` (script lives in `<template>/scripts/lib/`). */
export const TEMPLATE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
/** `<repo>` */
export const REPO_ROOT = path.resolve(TEMPLATE_ROOT, "..", "..");
export const OUT_DIR = path.join(TEMPLATE_ROOT, "out");

export function readJson(absolutePath) {
  return JSON.parse(readFileSync(absolutePath, "utf8"));
}

/**
 * Resolve a file inside `packages/contracts` through the package's own exports map, so the schema is
 * addressed as a package concern (documented consumer contract in packages/contracts/README.md).
 */
export function contractsFile(exportPath) {
  return require.resolve(`@ai-web-agency/contracts/${exportPath}`);
}

export const templateConfig = readJson(path.join(TEMPLATE_ROOT, "template.config.json"));
/**
 * The artifact under test. `template.config.json` declares the reference fixture; `CONTENT_FILE`
 * overrides it with a single client artifact (the build service writes
 * `content.generated.<client_id>.json` next to the fixture and passes the basename). Resolved
 * against `TEMPLATE_ROOT`, which is also the cwd of every npm workspace script.
 */
export const contentFile = process.env.CONTENT_FILE?.trim() || templateConfig.content_file;
export const contentPath = path.resolve(TEMPLATE_ROOT, contentFile);

const requestedPresetId =
  process.env.DESIGN_PRESET_ID?.trim()
  || process.argv.find((arg) => arg.startsWith("--preset="))?.slice("--preset=".length).trim();

function resolveDesignPresetPath() {
  if (!requestedPresetId) return path.resolve(TEMPLATE_ROOT, templateConfig.design_preset_file);
  if (!/^[a-z0-9-]+$/.test(requestedPresetId)) {
    throw new Error("DESIGN_PRESET_ID must contain only lowercase letters, digits and hyphens");
  }
  return path.join(REPO_ROOT, "sites", "_presets", `${requestedPresetId}.json`);
}

export const designPresetPath = resolveDesignPresetPath();

export const readContent = () => readJson(contentPath);
export const readDesignPreset = () => readJson(designPresetPath);
export const readContentSchema = () => readJson(contractsFile("content.schema.json"));

const relative = (absolute) => path.relative(REPO_ROOT, absolute).split(path.sep).join("/");
export const contentLabel = relative(contentPath);
export const designPresetLabel = relative(designPresetPath);

/** Same checklist shape as the build gate, so gate output can be read by a human and by CI. */
export function createReport(title) {
  const results = [];
  return {
    check(name, ok, detail = "") {
      results.push({ name, ok: Boolean(ok), detail });
      console.log(`[${ok ? "PASS" : "FAIL"}] ${name}${detail ? ` - ${detail}` : ""}`);
    },
    note(name, detail = "") {
      console.log(`[INFO] ${name}${detail ? ` - ${detail}` : ""}`);
    },
    finish() {
      const failed = results.filter((entry) => !entry.ok);
      console.log("");
      if (failed.length > 0) {
        console.error(
          `${title}: ${failed.length} check(s) failed -> ${failed.map((f) => f.name).join(", ")}`,
        );
        return 1;
      }
      console.log(`${title}: ${results.length} check(s) passed`);
      return 0;
    },
  };
}
