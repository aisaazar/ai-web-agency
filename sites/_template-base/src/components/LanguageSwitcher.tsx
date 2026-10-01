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
      <summary className="liquid-glass cursor-pointer list-none rounded-full px-3 py-2 text-xs font-semibold text-[hsl(var(--foreground))] shadow-sm backdrop-blur">
        DE <span aria-hidden="true">⌄</span>
      </summary>
      <div className="absolute right-0 top-full z-50 mt-2 w-44 rounded-2xl border border-white/20 bg-black/45 p-1 shadow-2xl backdrop-blur-xl">
        {LANGUAGES.map(([code, name]) => (
          <a
            key={code}
            href={translateUrl(code)}
            className="block rounded-lg px-3 py-2 text-sm text-white/75 hover:bg-white/10 hover:text-white"
            title={`${name} — automatic translation`}
          >
            {code.toUpperCase()} — {name}
          </a>
        ))}
      </div>
    </details>
  );
}
