#!/usr/bin/env node
/**
 * Cross-platform Python launcher for repo scripts.
 *
 * The repository owns its own virtual environment (`.venv`, gitignored) and never relies on a
 * globally installed interpreter, so that `python` on PATH (which may belong to an unrelated
 * project) can never be used by accident.
 *
 * Usage: node scripts/py.mjs <script.py> [args...]
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

const candidates =
  process.platform === "win32"
    ? [".venv/Scripts/python.exe"]
    : [".venv/bin/python", ".venv/bin/python3"];

const interpreter = candidates
  .map((rel) => path.join(repoRoot, rel))
  .find((abs) => existsSync(abs));

if (!interpreter) {
  console.error(
    [
      "No repository virtual environment found.",
      "",
      "Create it once with:",
      process.platform === "win32"
        ? "  py -3.12 -m venv .venv && .venv\\Scripts\\python.exe -m pip install -e apps/api"
        : "  python3 -m venv .venv && .venv/bin/python -m pip install -e apps/api",
    ].join("\n"),
  );
  process.exit(1);
}

const result = spawnSync(interpreter, process.argv.slice(2), {
  cwd: repoRoot,
  stdio: "inherit",
  env: { ...process.env, PYTHONPATH: "", PYTHONDONTWRITEBYTECODE: "1" },
});

process.exit(result.status ?? 1);
