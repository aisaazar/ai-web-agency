import Link from "next/link";

export interface NavItem {
  href: string;
  label: string;
}

/**
 * Primary navigation is server-rendered. Current-page styling is intentionally omitted here:
 * static export has no runtime pathname dependency, and removing it keeps navigation zero-JS.
 */
export function SiteNav({ items, ariaLabel }: { items: readonly NavItem[]; ariaLabel: string }) {
  return (
    <nav aria-label={ariaLabel}>
      <ul className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm font-medium">
        {items.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              prefetch={false}
              className="inline-flex min-h-6 items-center rounded-sm py-1 text-ink hover:text-brand-700 hover:underline"
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
