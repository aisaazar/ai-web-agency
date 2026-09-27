import { createServer } from "node:http";
import { gzipSync } from "node:zlib";
import { readFile, mkdir } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(root, "sites", "_template-base", "out");
const artifactsDir = path.join(root, ".artifacts");
const reportPath = path.join(artifactsDir, "lighthouse-build.json");
const mime = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};
const compressible = new Set([".html", ".css", ".js", ".txt", ".xml", ".json", ".svg"]);

const resolveOutput = async (pathname) => {
  const relative = pathname === "/" ? "index.html" : pathname.endsWith("/")
    ? pathname.slice(1) + "index.html"
    : pathname.slice(1);
  let file = path.join(outDir, relative);
  try {
    await readFile(file);
  } catch {
    file = path.join(outDir, relative, "index.html");
  }
  return file;
};

const server = createServer(async (req, res) => {
  try {
    const pathname = new URL(req.url, "http://localhost").pathname;
    const file = await resolveOutput(pathname);
    const data = await readFile(file);
    const ext = path.extname(file);
    const headers = {
      "content-type": mime[ext] || "application/octet-stream",
      "cache-control": pathname.startsWith("/_next/static/") || pathname.startsWith("/fonts/")
        ? "public, max-age=31536000, immutable"
        : "no-cache",
    };
    const acceptsGzip = String(req.headers["accept-encoding"] || "").includes("gzip");
    const shouldCompress = acceptsGzip && compressible.has(ext);
    if (shouldCompress) {
      headers["content-encoding"] = "gzip";
      headers.vary = "Accept-Encoding";
      res.writeHead(200, headers);
      res.end(gzipSync(data, { level: 9 }));
      return;
    }
    res.writeHead(200, headers);
    res.end(data);
  } catch {
    res.writeHead(404);
    res.end("not found");
  }
});

await mkdir(artifactsDir, { recursive: true });
await new Promise((resolve) => server.listen(4174, "127.0.0.1", resolve));

const args = [
  "lighthouse", "http://127.0.0.1:4174",
  "--output=json", "--output-path=" + reportPath,
  "--chrome-flags=--headless=new",
  "--only-categories=performance,accessibility,seo",
];
const child = spawn("npx", args, { cwd: root, shell: true, stdio: ["ignore", "pipe", "pipe"] });
let stdout = "";
let stderr = "";
child.stdout.on("data", (chunk) => { stdout += chunk; });
child.stderr.on("data", (chunk) => { stderr += chunk; });
const exitCode = await new Promise((resolve) => child.on("close", resolve));
server.close();

let report;
try {
  report = JSON.parse(await readFile(reportPath, "utf8"));
} catch {
  console.error(stdout + stderr);
  process.exit(exitCode || 1);
}

const scores = {
  performance: Math.round((report.categories.performance?.score ?? 0) * 100),
  accessibility: Math.round((report.categories.accessibility?.score ?? 0) * 100),
  seo: Math.round((report.categories.seo?.score ?? 0) * 100),
};
console.log(
  "lighthouse gate: performance=" + scores.performance +
  ", accessibility=" + scores.accessibility +
  ", seo=" + scores.seo,
);
if (scores.performance < 95) process.exit(1);
process.exit(0);
