"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    turnstile?: {
      render: (element: HTMLElement, options: { sitekey: string; callback: (token: string) => void; "expired-callback": () => void; "error-callback": () => void }) => string;
      reset: (widgetId?: string) => void;
    };
  }
}

const SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim();

export function TurnstileField({ onToken }: { onToken: (token: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!SITE_KEY || !ref.current) return;
    const render = () => {
      if (!ref.current || !window.turnstile) return;
      window.turnstile.render(ref.current, { sitekey: SITE_KEY, callback: onToken, "expired-callback": () => onToken(""), "error-callback": () => onToken("") });
    };
    const existing = document.querySelector('script[data-turnstile="1"]');
    if (existing) render();
    else {
      const script = document.createElement("script");
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
      script.async = true;
      script.defer = true;
      script.dataset.turnstile = "1";
      script.onload = render;
      document.head.appendChild(script);
    }
  }, [onToken]);
  return SITE_KEY ? <div ref={ref} aria-label="Cloudflare Turnstile" /> : null;
}
