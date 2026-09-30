import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

type Params = { params: Promise<{ leadId: string }> };

export async function POST(request: NextRequest, { params }: Params) {
  const { leadId } = await params;
  const session = request.cookies.get("agency_session")?.value;
  const csrf = request.cookies.get("agency_csrf")?.value;

  if (!session) return NextResponse.redirect(new URL("/login", request.url), 303);
  if (!csrf || !ORG_ID) {
    return NextResponse.json({ detail: "Dashboard authentication is not configured" }, { status: 500 });
  }

  const form = await request.formData();
  const status = String(form.get("status") ?? "").trim();
  const note = String(form.get("note") ?? "").trim() || null;
  const allowed = new Set(["new", "contacted", "qualified", "won", "lost"]);
  if (!allowed.has(status)) {
    return NextResponse.json({ detail: "Invalid lead status" }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(
      `${API_BASE_URL}/v1/leads/${encodeURIComponent(leadId)}/status?org_id=${encodeURIComponent(ORG_ID)}`,
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Cookie: `agency_session=${session}; agency_csrf=${csrf}`,
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({ status, note, actor: "dashboard" }),
        cache: "no-store",
      },
    );
  } catch {
    const target = new URL("/leads", request.url);
    target.searchParams.set("error", "Agency API is currently unavailable");
    return NextResponse.redirect(target, 303);
  }

  if (upstream.status === 401 || upstream.status === 403) {
    return NextResponse.redirect(new URL("/login", request.url), 303);
  }

  const target = new URL("/leads", request.url);
  if (!upstream.ok) {
    target.searchParams.set("error", (await upstream.text()).slice(0, 500) || "Lead update failed");
  } else {
    target.searchParams.set("result", `lead-${status}`);
  }
  return NextResponse.redirect(target, 303);
}