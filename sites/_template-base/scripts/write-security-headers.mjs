import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const outDir = path.resolve("out");
const agentApi = process.env.NEXT_PUBLIC_AGENCY_AGENT_API_URL;
const leadApi = process.env.NEXT_PUBLIC_AGENCY_LEAD_API_URL;
const production = process.env.PRODUCTION_BUILD === "1";

function originOf(value, name) {
  if (!value) return null;
  const url = new URL(value);
  if (production && url.protocol !== "https:") {
    throw new Error(`${name} must use HTTPS for production builds`);
  }
  if (url.username || url.password) {
    throw new Error(`${name} must not contain credentials`);
  }
  return url.origin;
}

const origins = [originOf(agentApi, "NEXT_PUBLIC_AGENCY_AGENT_API_URL"),
  originOf(leadApi, "NEXT_PUBLIC_AGENCY_LEAD_API_URL")].filter(Boolean);

function inlineScriptHashes() {
  const hashes = new Set();
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(file);
      else if (entry.isFile() && file.endsWith(".html")) {
        const html = fs.readFileSync(file, "utf8");
        const pattern = /<script\b(?![^>]*\bsrc\s*=)[^>]*>([\s\S]*?)<\/script>/gi;
        for (const match of html.matchAll(pattern)) {
          const digest = crypto.createHash("sha256").update(match[1], "utf8").digest("base64");
          hashes.add("'sha256-" + digest + "'");
        }
      }
    }
  }
  if (fs.existsSync(outDir)) walk(outDir);
  return [...hashes].sort();
}

fs.mkdirSync(outDir, { recursive: true });
const scriptSources = ["'self'", ...inlineScriptHashes()];
const connectSrc = ["'self'", ...origins];
const contentSecurityPolicy = [
  "default-src 'self'", "base-uri 'self'", "form-action 'self'",
  "frame-ancestors 'none'", "object-src 'none'", "img-src 'self' data:",
  "font-src 'self'", "style-src 'self'",
  `script-src ${scriptSources.join(" ")}`, `connect-src ${connectSrc.join(" ")}`,
].join("; ");

const config = {
  headers: [{ source: "/(.*)", headers: [
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "X-DNS-Prefetch-Control", value: "off" },
    { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(), payment=(), usb=()" },
    { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
    { key: "Content-Security-Policy", value: contentSecurityPolicy },
  ]}],
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "vercel.json"), JSON.stringify(config, null, 2) + "\n", "utf8");
console.log("Generated static security headers.");
