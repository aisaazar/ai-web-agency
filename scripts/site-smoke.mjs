import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(root, "sites", "_template-base", "out");
const routes = ["/", "/leistungen", "/impressum", "/datenschutz"];
const mime = { ".html": "text/html; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".xml": "application/xml" };

const server = createServer(async (req, res) => {
  try {
    const pathname = new URL(req.url, "http://localhost").pathname;
    const relative = pathname === "/" ? "index.html" : pathname.endsWith("/") ? `${pathname.slice(1)}index.html` : pathname.slice(1);
    let file = path.join(outDir, relative);
    try { await readFile(file); } catch { file = path.join(outDir, relative, "index.html"); }
    const data = await readFile(file);
    res.writeHead(200, { "content-type": mime[path.extname(file)] || "text/html; charset=utf-8" });
    res.end(data);
  } catch { res.writeHead(404); res.end("not found"); }
});

await new Promise((resolve) => server.listen(4173, "127.0.0.1", resolve));
const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const context = await browser.newContext();
const page = await context.newPage();
const consoleErrors = [];
page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
page.on("pageerror", (error) => consoleErrors.push(error.message));
try {
  const checkedLinks = new Set();
  for (const route of routes) {
    // `networkidle` is not a usable readiness signal on a client site: a production build that
    // passes the gate has Turnstile enabled, and Turnstile keeps talking to
    // challenges.cloudflare.com for as long as the page is open, so the network never goes idle.
    // `load` still requires every local subresource to arrive, and the assertions that follow -
    // route 200, h1 present, every internal link resolving, axe clean, form wired - are what
    // this smoke actually proves.
    const response = await page.goto(`http://127.0.0.1:4173${route}`, { waitUntil: "load" });
    if (!response || !response.ok()) throw new Error(`${route} returned ${response?.status()}`);
    if (await page.locator("h1").first().count() === 0) throw new Error(`${route} has no h1`);
    for (const href of await page.locator("a[href]").evaluateAll((links) => links.map((link) => link.getAttribute("href")))) {
      if (!href || !href.startsWith("/") || href.startsWith("//")) continue;
      checkedLinks.add(href.split("#")[0]);
    }
  }
  for (const href of checkedLinks) {
    const response = await page.goto(`http://127.0.0.1:4173${href}`, { waitUntil: "load" });
    if (!response || !response.ok()) throw new Error(`broken internal link: ${href} -> ${response?.status()}`);
  }

  await page.goto("http://127.0.0.1:4173/", { waitUntil: "networkidle" });
  const axe = await new AxeBuilder({ page }).analyze();
  const severe = axe.violations.filter((item) => item.impact === "critical" || item.impact === "serious");
  if (severe.length) throw new Error(`a11y violations: ${severe.map((item) => item.id).join(",")}`);

  for (const id of ["lead-name", "lead-email", "lead-message", "lead-consent"]) {
    if (await page.locator(`#${id}`).count() !== 1) throw new Error(`missing form field: ${id}`);
  }
  await page.locator("button[type=submit]").click();
  if (await page.getByRole("status").count() === 0) throw new Error("lead form has no status region");

  if (consoleErrors.length) throw new Error(`console errors: ${consoleErrors.join(" | ")}`);
  console.log(`site smoke passed: ${routes.length} routes, internal links=${checkedLinks.size}, axe serious/critical=0, form controls present`);
} finally {
  await context.close();
  await browser.close();
  server.close();
}
