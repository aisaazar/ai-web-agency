import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

export async function POST(request: NextRequest) {
  const session = request.cookies.get("agency_session")?.value;
  const csrf = request.cookies.get("agency_csrf")?.value;

  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url), 303);
  }
  if (!csrf || !ORG_ID) {
    return NextResponse.json(
      { detail: "Dashboard authentication is not configured" },
      { status: 500 },
    );
  }

  const form = await request.formData();
  const payload = {
    org_id: ORG_ID,
    client_name: String(form.get("client_name") ?? "").trim(),
    client_slug: String(form.get("client_slug") ?? "").trim(),
    category: String(form.get("category") ?? "dental").trim(),
    jurisdiction: String(form.get("jurisdiction") ?? "DE").trim(),
    locale: String(form.get("locale") ?? "de-DE").trim(),
    existing_url: String(form.get("existing_url") ?? "").trim() || null,
    facts: [],
  };

  const upstream = await fetch(`${API_BASE_URL}/v1/intake`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Cookie: `agency_session=${session}; agency_csrf=${csrf}`,
      "X-CSRF-Token": csrf,
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (upstream.status === 401 || upstream.status === 403) {
    return NextResponse.redirect(new URL("/login", request.url), 303);
  }
  if (!upstream.ok) {
    const body = await upstream.text();
    return NextResponse.json(
      { detail: body || "Intake request failed" },
      { status: upstream.status },
    );
  }

  return NextResponse.redirect(new URL("/clients?created=1", request.url), 303);
}
