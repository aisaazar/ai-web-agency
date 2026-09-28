#!/usr/bin/env node
/**
 * Secrets audit — docs/PLAN-14-DAYS.md Day 13 ("secrets audit") and docs/PRODUCTION-RUNBOOK.md.
 *
 * A client build never receives platform secrets: the static build runs without secret-like environment
 * names (apps/api/src/agency/services/site_build_service.py) and nothing secret belongs in an artefact.
 * This script is the repository-side half of that rule. It fails when
 *
 *   tracked_env      a tracked file is a real environment file instead of the .env.example template
 *   ignore_rules     .env is not git-ignored, so a local secret could be committed by accident
 *   credential_shape a tracked file carries credential-shaped material (private key, provider token)
 *   public_prefix    a NEXT_PUBLIC_* name looks secret, and everything in that namespace ships to browsers
 *
 * Offline and deterministic: `git ls-files` plus regular expressions, no network, no dependencies.
 *
 * Usage: node scripts/secrets-audit.mjs
 */
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const MAX_SCAN_BYTES = 400_000;

/** Credential shapes that are never legitimate in a tracked file. */
const CREDENTIAL_SHAPES = [
  { pattern: /-----BEGIN [A-Z ]*PRIVATE KEY-----/, reason: "private key material" },
  { pattern: /\bAKIA[0-9A-Z]{16}\b/, reason: "AWS access key id" },
  { pattern: /\bsk-(?:ant-|proj-|live-)?[A-Za-z0-9_-]{20,}\b/, reason: "OpenAI/Anthropic-style API key" },
  { pattern: /\bsk_live_[A-Za-z0-9]{16,}\b/, reason: "Stripe live secret key" },
  { pattern: /\bxox[abprs]-[A-Za-z0-9-]{10,}\b/, reason: "Slack token" },
  { pattern: /\bgh[pousr]_[A-Za-z0-9]{20,}\b/, reason: "GitHub token" },
  { pattern: /\bAIza[0-9A-Za-z_-]{35}\b/, reason: "Google API key" },
  { pattern: /\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b/, reason: "signed bearer token" },
];

/** A public prefix name that contains one of these words is a secret shipped to the browser. */
const PUBLIC_PREFIX = "NEXT_PUBLIC_";
const SECRET_NAME_MARKERS = ["API_KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "PRIVATE_KEY"];
const PUBLIC_SECRET_NAME = new RegExp(
  `\\b${PUBLIC_PREFIX}[A-Z0-9_]*(?:${SECRET_NAME_MARKERS.join("|")})[A-Z0-9_]*`,
  "u",
);

const findings = [];

function fail(check, detail) {
  findings.push({ check, detail });
}

function git(args) {
  return execFileSync("git", args, { cwd: root, encoding: "utf8" });
}

function isBinary(buffer) {
  return buffer.subarray(0, 8192).includes(0);
}

function trackedFiles() {
  try {
    return git(["ls-files", "-z"])
      .split("\0")
      .filter((entry) => entry.length > 0);
  } catch (error) {
    console.error(`secrets audit failed: cannot enumerate tracked files with git ls-files (${error.message})`);
    process.exit(1);
  }
}

function envFileCheck(files) {
  for (const file of files) {
    const name = path.basename(file);
    if (name === ".env.example") continue;
    if (name === ".env" || name.startsWith(".env.")) {
      fail("tracked_env", `${file} is a real environment file; only .env.example is tracked`);
    }
  }
  const ignored = git(["check-ignore", ".env"]).trim().length > 0;
  if (!ignored) {
    fail("ignore_rules", ".env is not git-ignored; a local secret could be committed by accident");
  }
  if (!existsSync(path.join(root, ".env.example"))) {
    fail("ignore_rules", ".env.example is missing: the configuration surface is undocumented");
  }
}

function scanFile(file) {
  const absolute = path.join(root, file);
  let stats;
  try {
    stats = statSync(absolute);
  } catch {
    return;
  }
  if (!stats.isFile() || stats.size > MAX_SCAN_BYTES) return;
  const buffer = readFileSync(absolute);
  if (isBinary(buffer)) return;
  const text = buffer.toString("utf8");
  text.split(/\r?\n/u).forEach((line, index) => {
    for (const rule of CREDENTIAL_SHAPES) {
      if (rule.pattern.test(line)) {
        fail("credential_shape", `${file}:${index + 1} looks like ${rule.reason}`);
      }
    }
    const publicName = line.match(PUBLIC_SECRET_NAME);
    if (publicName) {
      fail("public_prefix", `${file}:${index + 1} exposes ${publicName[0]} to browser builds`);
    }
  });
}

function main() {
  const files = trackedFiles();
  envFileCheck(files);
  for (const file of files) scanFile(file);

  for (const finding of findings) {
    console.error(`${finding.check}: ${finding.detail}`);
  }
  if (findings.length > 0) {
    console.error(`secrets audit failed: ${findings.length} finding(s) in ${files.length} tracked files`);
    process.exit(1);
  }
  console.log(
    `secrets audit passed: ${files.length} tracked files scanned, no credential shapes, ` +
      `no secret-like ${PUBLIC_PREFIX}* names, .env ignored`,
  );
}

main();
