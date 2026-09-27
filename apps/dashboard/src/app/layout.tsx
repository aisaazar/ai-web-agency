import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

const nav = [
  ["/", "Overview"], ["/clients", "Clients"], ["/pipeline", "Pipeline"],
  ["/artifacts", "Artifacts"], ["/deployments", "Deployments"], ["/leads", "Leads"],
] as const;

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><body><div className="shell">
    <aside className="sidebar"><div className="brand">AI Web Agency</div>
      <nav className="nav" aria-label="Dashboard">
        {nav.map(([href,label]) => <Link key={href} href={href}>{label}</Link>)}
      </nav>
    </aside>
    <main className="main">{children}</main>
  </div></body></html>;
}
