import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

export async function POST(request: NextRequest) {
  const session = request.cookies.get("agency_session")?.value;
  const csrf = request.cookies.get("agency_csrf")?.value;

  if (!session) return NextResponse.redirect(new URL("/login", request.url), 303);
  if (!csrf || !ORG_ID) {
    return NextResponse.json(
      { detail: "Dashboard authentication is not configured" },
      { status: 500 },
    );
  }

  const form = await request.formData();
  const body = {
    org_id: ORG_ID,
    name: String(form.get("name") ?? "").trim(),
    category: String(form.get("category") ?? "").trim(),
    city: String(form.get("city") ?? "").trim() || null,
    country: "DE",
    website_url: String(form.get("website_url") ?? "").trim() || null,
    source_url: String(form.get("source_url") ?? "").trim() || null,
    source_kind: String(form.get("source_kind") ?? "manual").trim(),
    contactability: String(form.get("contactability") ?? "unknown").trim(),

    website_status: String(form.get("website_status") ?? "unknown").trim(),
    notes: String(form.get("notes") ?? "").trim() || null,
  };

  let upstream: Response;
  try {
    upstream = await fetch(API_BASE_URL + "/v1/prospects", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: "agency_session=" + session + "; agency_csrf=" + csrf,
        "X-CSRF-Token": csrf,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return NextResponse.redirect(
      new URL("/prospects?error=Agency%20API%20is%20currently%20unavailable", request.url),
      303,
    );
  }
  if (upstream.status === 401) {
    return NextResponse.redirect(new URL("/login", request.url), 303);
  }

  if (upstream.status === 403) {
    return NextResponse.redirect(
      new URL("/prospects?error=You%20do%20not%20have%20permission%20to%20add%20prospects", request.url),
      303,
    );
  }
  if (!upstream.ok) {
    return NextResponse.json(
      { detail: await upstream.text() },
      { status: upstream.status },
    );
  }
  return NextResponse.redirect(
    new URL("/prospects?result=Prospect%20added%20and%20prioritized", request.url),
    303,
  );
}
