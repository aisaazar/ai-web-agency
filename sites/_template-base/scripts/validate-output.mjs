import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.resolve(root, process.env.OUTPUT_DIR?.trim() || "out");
const required = [
  "index.html",
  "leistungen/index.html",
  "impressum/index.html",
  "datenschutz/index.html",
  "sitemap.xml",
  "robots.txt",
  "llms.txt"
];
for (const rel of required) await access(path.join(outDir, rel));
const index = await readFile(path.join(outDir, "index.html"), "utf8");
const markers = (process.env.OUTPUT_MARKERS?.split(",").map((value) => value.trim()).filter(Boolean))
  ?? ["Zahnbalance Nürnberg", "Leistungen", "Impressum"];
for (const marker of markers) {
  if (!index.includes(marker)) throw new Error("missing build marker: " + marker);
}

const vercel = JSON.parse(await readFile(path.join(outDir, "vercel.json"), "utf8"));
const headers = vercel.headers?.find((item) => item.source === "/(.*)")?.headers ?? [];
const header = (name) => headers.find((item) => item.key === name)?.value ?? "";
const csp = header("Content-Security-Policy");
for (const requiredHeader of [
  ["X-Content-Type-Options", "nosniff"],
  ["X-Frame-Options", "DENY"],
  ["Referrer-Policy", "strict-origin-when-cross-origin"],
  ["Strict-Transport-Security", "max-age=31536000; includeSubDomains"],
]) {
  if (header(requiredHeader[0]) !== requiredHeader[1]) throw new Error("missing security header: " + requiredHeader[0]);
}
for (const marker of ["default-src 'self'", "object-src 'none'", "frame-ancestors 'none'", "connect-src 'self'"]) {
  if (!csp.includes(marker)) throw new Error("incomplete CSP: " + marker);
}
if (csp.includes("'unsafe-inline'") || !/script-src[^;]*'sha256-/u.test(csp)) {
  throw new Error("CSP must use script hashes instead of unsafe-inline");
}
const files = await readdir(outDir, { recursive: true });
const banned = ["fonts.googleapis.com", "fonts.gstatic.com", "googletagmanager.com", "google-analytics.com", "connect.facebook.net"];
for (const rel of files.filter((item) => item.endsWith(".html"))) {
  const html = await readFile(path.join(outDir, rel), "utf8");
  for (const marker of banned) if (html.includes(marker)) throw new Error("third-party asset/tracker found: " + marker);
}
console.log("static output validation passed");
