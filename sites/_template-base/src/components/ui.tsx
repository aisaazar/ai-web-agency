import type { ReactNode } from "react";

/** Layout primitives. Every section is a landmark with an accessible name. */

export function Container({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`mx-auto w-full max-w-5xl px-4 sm:px-6 lg:px-8 ${className}`}>{children}</div>;
}

export function Section({
  id,
  labelledBy,
  children,
  className = "",
  as: Tag = "section",
}: {
  id?: string;
  labelledBy?: string;
  children: ReactNode;
  className?: string;
  as?: "section" | "div";
}) {
  return (
    <Tag id={id} aria-labelledby={labelledBy} className={`py-12 sm:py-16 ${className}`}>
      <Container>{children}</Container>
    </Tag>
  );
}

export function SectionHeading({
  id,
  eyebrow,
  children,
}: {
  id: string;
  eyebrow?: string;
  children: ReactNode;
}) {
  return (
    <div className="mb-6">
      {eyebrow ? (
        <p className="mb-2 text-sm font-semibold tracking-wide text-brand-600 uppercase">{eyebrow}</p>
      ) : null}
      <h2 id={id} className="text-2xl font-semibold text-balance text-ink sm:text-3xl">
        {children}
      </h2>
    </div>
  );
}

/**
 * Renders `list[str]` paragraphs from the content model. Plain text only — the content contract has
 * no HTML or markdown field on purpose, so no sanitizer is ever needed
 * (`docs/SECURITY-AND-RISKS.md`).
 */
export function Paragraphs({ items, className = "" }: { items: readonly string[]; className?: string }) {
  return (
    <div className={`space-y-4 text-ink-muted ${className}`}>
      {items.map((paragraph) => (
        <p key={paragraph.slice(0, 40)}>{paragraph}</p>
      ))}
    </div>
  );
}

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-line bg-surface-muted p-5 sm:p-6 ${className}`}>
      {children}
    </div>
  );
}

/** First focusable element of the document: keyboard users reach the content in one tab. */
export function SkipLink({ label }: { label: string }) {
  return (
    <a
      href="#main"
      className="sr-only rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-surface focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50"
    >
      {label}
    </a>
  );
}
