"use client";

import { useEffect, useState } from "react";

const LABELS = {
  de: { text: "DE", aria: "Sprache auswählen" },
  en: { text: "EN", aria: "Select language" },
} as const;

export function LanguageSwitcher() {
  const [currentUrl, setCurrentUrl] = useState("");

  useEffect(() => {
    setCurrentUrl(window.location.href);
  }, []);

  const englishUrl = currentUrl
    ? "https://translate.google.com/translate?sl=auto&tl=en&u=" + encodeURIComponent(currentUrl)
    : "https://translate.google.com/";

  return (
    <div className="inline-flex items-center rounded-md border border-line bg-surface/95 p-1 text-xs font-semibold backdrop-blur">
      <span className="sr-only">{LABELS.de.aria}</span>
      <span
        aria-current="page"
        className="rounded px-2 py-1 text-brand-700"
        title="Deutsch"
      >
        {LABELS.de.text}
      </span>
      <a
        href={englishUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="rounded px-2 py-1 text-ink-muted hover:bg-brand-50 hover:text-brand-700"
        title="English — automatic translation"
      >
        {LABELS.en.text}
      </a>
    </div>
  );
}
