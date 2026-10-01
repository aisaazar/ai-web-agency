"use client";

import { useEffect, useState } from "react";

const LANGUAGES = [
  ["de", "Deutsch"],
  ["en", "English"],
  ["fr", "Français"],
  ["es", "Español"],
  ["it", "Italiano"],
  ["tr", "Türkçe"],
  ["ar", "العربية"],
  ["fa", "فارسی"],
] as const;

export function LanguageSwitcher() {
  const [currentUrl, setCurrentUrl] = useState("");

  useEffect(() => {
    setCurrentUrl(window.location.href);
  }, []);

  const translateUrl = (language: string) =>
    currentUrl
      ? `https://translate.google.com/translate?sl=auto&tl=${language}&u=${encodeURIComponent(currentUrl)}`
      : "https://translate.google.com/";

  return (
    <details className="relative">
      <summary className="cursor-pointer list-none rounded-md border border-line bg-surface/95 px-3 py-2 text-xs font-semibold text-brand-700 shadow-sm backdrop-blur">
        DE <span aria-hidden="true">⌄</span>
      </summary>
      <div className="absolute right-0 top-full z-50 mt-2 w-40 rounded-lg border border-line bg-surface p-1 shadow-xl">
        {LANGUAGES.map(([code, name]) => (
          <a
            key={code}
            href={translateUrl(code)}
            className="block rounded-md px-3 py-2 text-sm text-ink hover:bg-brand-50 hover:text-brand-700"
            title={`${name} — automatic translation`}
          >
            {code.toUpperCase()} — {name}
          </a>
        ))}
      </div>
    </details>
  );
}
