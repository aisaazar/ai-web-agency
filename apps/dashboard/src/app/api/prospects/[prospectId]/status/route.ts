import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ prospectId: string }> },
) {
  const session = request.cookies.get("agency_session")?.value;
  const csrf = request.cookies.get("agency_csrf")?.value;
  const { prospectId } = await params;

  if (!session) return NextResponse.redirect(new URL("/login", request.url), 303);
  if (!csrf || !ORG_ID) {
    return NextResponse.redirect(
      new URL("/prospects?error=Dashboard%20authentication%20is%20not%20configured", request.url),
      303,
    );
  }

  const form = await request.formData();
  const status = String(form.get("status") ?? "").trim();
  const note = String(form.get("note") ?? "").trim() || null;

  let upstream: Response;
  try {
    upstream = await fetch(
      API_BASE_URL +
        "/v1/prospects/" +
        encodeURIComponent(prospectId) +
        "/status?org_id=" +
        encodeURIComponent(ORG_ID),
      {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Cookie: "agency_session=" + session + "; agency_csrf=" + csrf,
          "X-CSRF-Token": csrf,
        },
        body: JSON.stringify({ status, note }),
        cache: "no-store",
      },
    );
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
      new URL("/prospects?error=You%20do%20not%20have%20permission%20to%20update%20prospects", request.url),
      303,
    );
  }
  if (!upstream.ok) {
    const detail = encodeURIComponent((await upstream.text()).slice(0, 180));
    return NextResponse.redirect(
      new URL("/prospects?error=Prospect%20update%20failed:%20" + detail, request.url),
      303,
    );
  }

  return NextResponse.redirect(
    new URL("/prospects?result=Prospect%20status%20updated", request.url),
    303,
  );
}
