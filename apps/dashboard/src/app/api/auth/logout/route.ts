import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";

export async function POST(request: NextRequest) {
  const session = request.cookies.get("agency_session")?.value;
  const csrf = request.cookies.get("agency_csrf")?.value;

  if (session) {
    try {
      await fetch(`${API_BASE_URL}/v1/auth/logout`, {
        method: "POST",
        headers: {
          Cookie: `agency_session=${session}; agency_csrf=${csrf ?? ""}`,
          "X-CSRF-Token": csrf ?? "",
        },
        cache: "no-store",
      });
    } catch {
      // Clear the dashboard session even if the upstream API is unavailable.
    }
  }

  const response = NextResponse.redirect(new URL("/login", request.url), 303);
  response.cookies.delete("agency_session");
  response.cookies.delete("agency_csrf");
  return response;
}
