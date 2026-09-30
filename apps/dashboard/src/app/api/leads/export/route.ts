import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

export async function GET(request: NextRequest) {
  const session = request.cookies.get("agency_session")?.value;

  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url), 303);
  }
  if (!ORG_ID) {
    return NextResponse.json(
      { detail: "AGENCY_ORG_ID is required for dashboard API access" },
      { status: 500 },
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(
      `${API_BASE_URL}/v1/leads/export.csv?org_id=${encodeURIComponent(ORG_ID)}`,
      {
        cache: "no-store",
        headers: { Cookie: `agency_session=${session}` },
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

  const body = await upstream.text();
  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "text/csv; charset=utf-8",
      "Content-Disposition": upstream.headers.get("content-disposition") ??
        "attachment; filename=leads.csv",
    },
  });
}
