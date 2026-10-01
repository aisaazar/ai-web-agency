import "./globals.css";
import { cookies } from "next/headers";
import type { ReactNode } from "react";
import Sidebar from "./_components/sidebar";

export const metadata = {
  title: {
    default: "AI Web Agency",
    template: "%s · AI Web Agency",
  },
  description: "Agency operations dashboard",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const session = (await cookies()).get("agency_session")?.value;

  return (
    <html lang="en">
      <body>
        <a className="skipLink" href="#main-content">Skip to main content</a>
        <div className={session ? "shell" : "authShell"}>
          {session ? <Sidebar onSignOut="/api/auth/logout" /> : null}
          <main className="main" id="main-content" tabIndex={-1}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
