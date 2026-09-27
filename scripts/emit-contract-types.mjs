#!/usr/bin/env node
/**
 * JSON Schema -> TypeScript, the last step of the one-directional content contract (ADR-004):
 *
 *   Pydantic (apps/api/src/agency/domain/content_model.py)
 *     -> JSON Schema (packages/contracts/content.schema.json)   [scripts/export_contracts.py]
 *        -> TypeScript (packages/contracts/src/content.ts)       [this script]
 *
 * The output is committed and must never be hand-edited. Run `npm run contracts` after any change
 * to the Pydantic model.
 */
import { readFile, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const schemaPath = path.join(repoRoot, "packages", "contracts", "content.schema.json");
const outPath = path.join(repoRoot, "packages", "contracts", "src", "content.ts");

const bannerComment = `/* eslint-disable */
/**
 * Generated file - DO NOT EDIT.
 *
 * Source of truth: apps/api/src/agency/domain/content_model.py
 * Chain: Pydantic -> JSON Schema -> TypeScript (docs/CONTRACTS-AND-CONVENTIONS.md, ADR-004).
 * Regenerate with: npm run contracts
 */`;

let compile;
try {
  ({ compile } = await import("json-schema-to-typescript"));
} catch {
  console.error(
    "json-schema-to-typescript is not installed. Run `npm install` at the repository root first.",
  );
  process.exit(1);
}

const schema = JSON.parse(await readFile(schemaPath, "utf8"));
const typescript = await compile(schema, schema.title ?? "ContentModel", {
  bannerComment,
  additionalProperties: false,
  declareExternallyReferenced: true,
  style: { semi: true, singleQuote: false, bracketSpacing: true },
});

await writeFile(outPath, `${typescript.trimEnd()}\n`, "utf8");

// Keep the formatting identical regardless of who runs this (no prettier drift).
spawnSync(process.execPath, [path.join(repoRoot, "node_modules", "prettier", "bin", "prettier.cjs"), "--write", outPath], {
  cwd: repoRoot,
  stdio: "ignore",
});

console.log(`wrote ${path.relative(repoRoot, outPath)}`);
