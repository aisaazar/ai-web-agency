import { content, isFixtureBuild } from "@/lib/content";
import { Container } from "./ui";

/**
 * Visible fixture banner. Fixture content exists to develop the template; it must never be mistaken
 * for a client site. The build gate blocks fixture content in production mode.
 */
export function FixtureNotice() {
  if (!isFixtureBuild) {
    return null;
  }

  return (
    <aside
      role="note"
      aria-label="Hinweis zu Demo-Inhalten"
      className="border-b border-accent-100 bg-accent-100"
    >
      <Container className="py-1">
        <p className="text-xs text-accent-700">
          <strong className="font-semibold">Demo-Inhalt (Fixture)</strong> — nur Vorschau, nicht zur
          Veröffentlichung. Datensatz: <span className="font-mono">{content.meta.client_slug}</span>.
        </p>
      </Container>
    </aside>
  );
}
