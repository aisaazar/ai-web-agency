import "./globals.css";
import Link from "next/link";
import { cookies } from "next/headers";
import type { ReactNode } from "react";

const nav = [
  ["/", "Overview"], ["/clients", "Clients"], ["/pipeline", "Pipeline"],
  ["/artifacts", "Artifacts"], ["/deployments", "Deployments"], ["/leads", "Leads"],
] as const;

export default async function RootLayout({ children }: { children: ReactNode }) {
  const session = (await cookies()).get("agency_session")?.value;
  return <html lang="en"><body><div className="shell">
    <aside className="sidebar"><div className="brand">AI Web Agency</div>
      <nav className="nav" aria-label="Dashboard">
        {nav.map(([href,label]) => <Link key={href} href={href}>{label}</Link>)}
        {session ? <form action="/api/auth/logout" method="post"><button className="navButton" type="submit">Sign out</button></form> : null}
      </nav>
    </aside>
    <main className="main">{children}</main>
  </div></body></html>;
}
