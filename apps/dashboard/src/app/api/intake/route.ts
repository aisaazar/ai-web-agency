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
  const rawFacts = String(form.get("facts") ?? "").trim();
  const factLines = rawFacts.split(/\r?\n/u).map((line) => line.trim()).filter(Boolean);
  const facts = factLines.map((line) => {
    const separator = line.indexOf("=");
    if (separator <= 0 || separator === line.length - 1) return null;
    const key = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).trim();
    if (!key || !value) return null;
    return { key, value, value_type: "text", source_kind: "dashboard", source_ref: "manual-intake", confidence: 1 };
  });
  if (facts.length === 0 || facts.some((fact) => fact === null)) {
    return NextResponse.json(
      { detail: "Provide at least one fact using key=value, one fact per line." },
      { status: 400 },
    );
  }
  const validFacts = facts.filter((fact): fact is NonNullable<typeof fact> => fact !== null);
  const presetId = String(form.get("preset_id") ?? "health").trim();
  if (!["health", "corporate", "warm"].includes(presetId)) {
    return NextResponse.json({ detail: "Invalid design preset" }, { status: 400 });
  }

  const payload = {
    org_id: ORG_ID,
    client_name: String(form.get("client_name") ?? "").trim(),
    client_slug: String(form.get("client_slug") ?? "").trim(),
    category: String(form.get("category") ?? "dental").trim(),
    jurisdiction: String(form.get("jurisdiction") ?? "DE").trim(),
    locale: String(form.get("locale") ?? "de-DE").trim(),
    existing_url: String(form.get("existing_url") ?? "").trim() || null,
    facts: [
      ...validFacts,
      { key: "selected_preset_id", value: presetId, value_type: "text", source_kind: "dashboard", source_ref: "template-gallery", confidence: 1 },
    ],
  };

  let upstream: Response;
  try {
    upstream = await fetch(`${API_BASE_URL}/v1/intake`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `agency_session=${session}; agency_csrf=${csrf}`,
        "X-CSRF-Token": csrf,
      },
      body: JSON.stringify(payload),
      cache: "no-store",
    });
  } catch {
    const target = new URL("/clients/new", request.url);
    target.searchParams.set("error", "Agency API is currently unavailable");
    return NextResponse.redirect(target, 303);
  }

  if (upstream.status === 401) {
    return NextResponse.redirect(new URL("/login", request.url), 303);
  }
  if (upstream.status === 403) {
    const target = new URL("/clients/new", request.url);
    target.searchParams.set("error", "You do not have permission to create clients");
    return NextResponse.redirect(target, 303);
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
