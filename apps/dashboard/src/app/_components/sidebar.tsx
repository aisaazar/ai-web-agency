"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type NavItem = {
  href: string;
  label: string;
  icon: ReactNode;
};

const iconProps = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

const nav: NavItem[] = [
  { href: "/", label: "Overview", icon: <svg {...iconProps}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg> },
  { href: "/clients", label: "Clients", icon: <svg {...iconProps}><path d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" /><circle cx="9.5" cy="7" r="4" /><path d="M19 8v6M22 11h-6" /></svg> },
  { href: "/templates", label: "Templates", icon: <svg {...iconProps}><rect x="3" y="4" width="7" height="7" rx="1" /><rect x="14" y="4" width="7" height="7" rx="1" /><rect x="3" y="13" width="7" height="7" rx="1" /><rect x="14" y="13" width="7" height="7" rx="1" /></svg> },
  { href: "/pipeline", label: "Pipeline", icon: <svg {...iconProps}><path d="M4 6h16M7 12h10M10 18h4" /><path d="M4 6l3 6v6h10v-6l3-6" /></svg> },
  { href: "/artifacts", label: "Artifacts", icon: <svg {...iconProps}><path d="M6 3h9l3 3v15H6z" /><path d="M14 3v4h4M9 12h6M9 16h6" /></svg> },
  { href: "/deployments", label: "Deployments", icon: <svg {...iconProps}><path d="M12 3v12M8 7l4-4 4 4M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" /></svg> },
  { href: "/leads", label: "Leads", icon: <svg {...iconProps}><path d="M4 4h16v13H5l-1 3z" /><path d="M8 8h8M8 12h5" /></svg> },
  { href: "/prospects", label: "Prospects", icon: <svg {...iconProps}><circle cx="11" cy="11" r="7" /><path d="m16.5 16.5 4 4M11 7v8M8 11h6" /></svg> },
  { href: "/costs", label: "LLM costs", icon: <svg {...iconProps}><circle cx="12" cy="12" r="8" /><path d="M14.5 8.5c-.7-.5-1.6-.8-2.5-.8-1.5 0-2.7.8-2.7 1.9s1.1 1.7 2.7 2c1.6.3 2.7.9 2.7 2s-1.2 2-2.7 2c-.9 0-1.8-.3-2.5-.8M12 6v12" /></svg> },
  { href: "/audit", label: "Audit log", icon: <svg {...iconProps}><circle cx="12" cy="12" r="8" /><path d="M12 8v4l2.5 2" /></svg> },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
export default function Sidebar({ onSignOut }: { onSignOut: string }) {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <Link className="brand" href="/" aria-label="AI Web Agency overview">
        <span className="brandMark" aria-hidden="true">AW</span>
        <span>AI Web Agency</span>
      </Link>
      <div className="sidebarLabel">Workspace</div>
      <nav className="nav" aria-label="Dashboard">
        {nav.map(({ href, label, icon }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              className={`navLink${active ? " active" : ""}`}
              aria-current={active ? "page" : undefined}
            >
              <span className="navIcon">{icon}</span>
              <span>{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="sidebarFooter">
        <div className="workspaceStatus">
          <span className="statusDot" aria-hidden="true" />
          <span>Operational</span>
        </div>
        <form action={onSignOut} method="post">
          <button className="navButton" type="submit">
            <span className="navIcon" aria-hidden="true">
              <svg {...iconProps}><path d="M10 17l5-5-5-5M15 12H3M21 3v18" /></svg>
            </span>
            <span>Sign out</span>
          </button>
        </form>
      </div>
    </aside>
  );
}
