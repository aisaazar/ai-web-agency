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
 *
 * Usage:
 *   node scripts/emit-contract-types.mjs           # write the generated TypeScript contract
 *   node scripts/emit-contract-types.mjs --check   # fail if the committed file is stale
 */
import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const schemaPath = path.join(repoRoot, "packages", "contracts", "content.schema.json");
const outPath = path.join(repoRoot, "packages", "contracts", "src", "content.ts");

// Line endings are not content: `.gitattributes` pins LF in every clone, and a CRLF checkout must
// never make a byte comparison report drifted contract (the trap `npm run tokens:check` hit before
// the attributes file existed).
const normalizeEol = (text) => text.replace(/\r\n/g, "\n");

const bannerComment = `/* eslint-disable */
/**
 * Generated file - DO NOT EDIT.
 *
 * Source of truth: apps/api/src/agency/domain/content_model.py
 * Chain: Pydantic -> JSON Schema -> TypeScript (docs/CONTRACTS-AND-CONVENTIONS.md, ADR-004).
 * Regenerate with: npm run contracts
 */`;

let compile;
let format;
try {
  ({ compile } = await import("json-schema-to-typescript"));
  ({ format } = await import("prettier"));
} catch {
  console.error(
    "json-schema-to-typescript and prettier are required. Run `npm install` at the repository root first.",
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

// Prettier is applied in-process so that the writer and the drift check format with exactly the
// same engine; a spawned `prettier --write` could silently disagree with the check.
const rendered = await format(`${typescript.trimEnd()}\n`, { filepath: outPath });
const relative = path.relative(repoRoot, outPath).replaceAll("\\", "/");

// `contracts:check` covers both generated artefacts (README): a hand-edited `content.ts` would
// otherwise ship a template typed against a contract the model no longer produces.
if (process.argv.includes("--check")) {
  const committed = existsSync(outPath) ? await readFile(outPath, "utf8") : null;
  if (committed !== null && normalizeEol(committed) === normalizeEol(rendered)) {
    console.log(`unchanged ${relative}`);
    process.exit(0);
  }
  console.error(`STALE ${relative}: regenerate with \`npm run contracts\``);
  process.exit(1);
}

await writeFile(outPath, rendered, "utf8");

console.log(`wrote ${relative}`);
