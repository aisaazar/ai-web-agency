import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const required = [
  "out/index.html",
  "out/leistungen/index.html",
  "out/impressum/index.html",
  "out/datenschutz/index.html",
  "out/sitemap.xml",
  "out/robots.txt",
  "out/llms.txt"
];
for (const rel of required) await access(path.join(root, rel));
const index = await readFile(path.join(root, "out", "index.html"), "utf8");
for (const marker of ["Zahnbalance Nürnberg", "Leistungen", "Impressum"]) {
  if (!index.includes(marker)) throw new Error("missing build marker: " + marker);
}
console.log("static output validation passed");
