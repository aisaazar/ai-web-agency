import type { Metadata, Viewport } from "next";

import "./globals.css";

import { FixtureNotice } from "@/components/FixtureNotice";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { SkipLink } from "@/components/ui";
import { content, origin, pageSeo } from "@/lib/content";
import { UI } from "@/lib/ui-strings";

/**
 * Root layout. `lang` comes from the content artifact, so a second language is a second artifact,
 * not a hardcoded attribute. The font preload is a same-origin, self-hosted woff2 — the only
 * subresource the first paint needs.
 */
export const metadata: Metadata = {
  metadataBase: new URL(`${origin}/`),
  title: { default: pageSeo("/").title, template: "%s" },
  description: content.site.description,
  applicationName: content.site.name,
  creator: content.business.legal_name,
  icons: { icon: "/favicon.svg" },
  // No telephone auto-detection: iOS would otherwise turn opening hours and prices into call links.
  formatDetection: { telephone: false, address: false, email: false },
};

const turnstileEnabled = Boolean(process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY?.trim());

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Zooming is never blocked (WCAG 1.4.4) and the token colour is declared for mobile browser chrome.
  themeColor: content.site.theme_color,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang={content.locale}>
      <head>
        <link
          rel="preload"
          href="/fonts/inter-latin.woff2"
          as="font"
          type="font/woff2"
          crossOrigin="anonymous"
        />
        {turnstileEnabled ? (
          <link rel="preconnect" href="https://challenges.cloudflare.com" crossOrigin="anonymous" />
        ) : null}
      </head>
      <body className="flex min-h-screen flex-col">
        <SkipLink label={UI.skipToContent} />
        <FixtureNotice />
        <SiteHeader />
        <main id="main" className="flex-1">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
