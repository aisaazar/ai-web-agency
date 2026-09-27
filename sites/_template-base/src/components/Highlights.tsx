import { content } from "@/lib/content";
import { Icon } from "./Icon";

/**
 * Trust highlights as a plain list. Rendered inside the hero section (the content model has no
 * heading field for this list, and the template deliberately invents no copy that should be part of
 * the content contract).
 */
export function Highlights() {
  const { highlights } = content;

  return (
    <ul className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {highlights.map((highlight) => (
        <li key={highlight.title} className="rounded-lg border border-line bg-surface p-5">
          <span className="mb-3 inline-flex rounded-md bg-brand-50 p-2 text-brand-700">
            <Icon name={highlight.icon} />
          </span>
          <h2 className="text-base font-semibold text-ink">{highlight.title}</h2>
          <p className="mt-2 text-sm text-ink-muted">{highlight.body}</p>
        </li>
      ))}
    </ul>
  );
}

