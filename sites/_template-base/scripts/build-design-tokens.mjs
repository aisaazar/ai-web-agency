#!/usr/bin/env node
/**
 * Design preset -> Tailwind v4 `@theme` CSS, plus a WCAG 2.1 contrast check of the preset itself.
 *
 * `docs/AI-AND-PROVIDERS.md` §1: design tokens, colour, contrast and fonts are deterministic code,
 * never a model decision. ADR-016 forbids per-client template forks, so one preset file compiles to
 * one CSS file. A preset that fails its own contrast budget fails here, not in a Lighthouse run.
 *
 * Usage:
 *   node scripts/build-design-tokens.mjs           # write the generated CSS
 *   node scripts/build-design-tokens.mjs --check   # fail if the generated CSS is stale
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

import { TEMPLATE_ROOT, createReport, designPresetLabel, readDesignPreset } from "./lib/paths.mjs";

const OUTPUT_PATH = path.join(TEMPLATE_ROOT, "src", "styles", "design-tokens.generated.css");
const HEX_PATTERN = /^#[0-9A-Fa-f]{6}$/;

const channelToLinear = (value) => {
  const channel = value / 255;
  return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
};

function relativeLuminance(hex) {
  return (
    0.2126 * channelToLinear(Number.parseInt(hex.slice(1, 3), 16)) +
    0.7152 * channelToLinear(Number.parseInt(hex.slice(3, 5), 16)) +
    0.0722 * channelToLinear(Number.parseInt(hex.slice(5, 7), 16))
  );
}

function contrastRatio(foreground, background) {
  const lighter = Math.max(relativeLuminance(foreground), relativeLuminance(background));
  const darker = Math.min(relativeLuminance(foreground), relativeLuminance(background));
  return (lighter + 0.05) / (darker + 0.05);
}

function render(preset) {
  const { colors, radius, fonts } = preset.tokens;
  const lines = [
    "/* GENERATED FILE - DO NOT EDIT.",
    " *",
    ` * Source: ${designPresetLabel} (preset id: ${preset.id}, version ${preset.version})`,
    " * Generator: sites/_template-base/scripts/build-design-tokens.mjs",
    " * Regenerate with: npm run tokens",
    " *",
    " * The contrast pairs declared in the preset were verified with WCAG 2.1 math by the generator.",
    " */",
    "",
    "@theme {",
    `  --font-sans: ${fonts.sans};`,
    "",
  ];
  for (const [name, value] of Object.entries(colors)) {
    lines.push(`  --color-${name}: ${value};`);
  }
  lines.push("");
  for (const [name, value] of Object.entries(radius)) {
    lines.push(`  --radius-${name}: ${value};`);
  }
  lines.push("}", "", ":root {", `  --color-focus-ring: ${colors.focus ?? colors["brand-600"]};`, "}", "");
  return lines.join("\n");
}

const report = createReport("design tokens");
const checkOnly = process.argv.includes("--check");
const preset = readDesignPreset();
const colors = preset.tokens?.colors ?? {};

report.check("preset id", typeof preset.id === "string" && preset.id.length > 0, preset.id);
report.check(
  "preset structure",
  Boolean(preset.tokens?.radius && preset.tokens?.fonts?.sans),
  `${Object.keys(colors).length} colours`,
);

const invalidColors = Object.entries(colors)
  .filter(([, value]) => !HEX_PATTERN.test(String(value)))
  .map(([name]) => name);
report.check("colours are 6-digit hex", invalidColors.length === 0, invalidColors.join(", "));

let contrastOk = true;
for (const pair of preset.tokens?.contrastPairs ?? []) {
  const foreground = colors[pair.foreground];
  const background = colors[pair.background];
  if (!foreground || !background) {
    report.check(`contrast ${pair.foreground}/${pair.background}`, false, "token missing");
    contrastOk = false;
    continue;
  }
  const ratio = contrastRatio(foreground, background);
  const ok = ratio >= pair.minRatio;
  contrastOk = contrastOk && ok;
  report.check(
    `contrast ${pair.foreground} on ${pair.background} >= ${pair.minRatio}:1`,
    ok,
    `${ratio.toFixed(2)}:1 (${pair.usage})`,
  );
}

const css = render(preset);
const current = existsSync(OUTPUT_PATH) ? readFileSync(OUTPUT_PATH, "utf8") : null;
if (current === css) {
  report.check("generated CSS up to date", true, "src/styles/design-tokens.generated.css");
} else if (checkOnly) {
  report.check("generated CSS up to date", false, "STALE - run `npm run tokens`");
} else {
  // The output directory is not tracked in git (an empty directory cannot be), so create it here
  // instead of relying on it existing in a fresh clone. ADR-004's "generated, never hand-edited"
  // rule only works if regeneration is a single command.
  mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
  writeFileSync(OUTPUT_PATH, css, "utf8");
  report.check("wrote src/styles/design-tokens.generated.css", true, `${css.length} bytes`);
}

if (!contrastOk) {
  console.error("design tokens: contrast budget not met - refusing to ship the preset");
}

process.exit(report.finish() | (contrastOk ? 0 : 1));
