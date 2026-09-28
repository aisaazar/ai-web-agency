import { NextRequest, NextResponse } from "next/server";

const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

type Params = { params: Promise<{ clientId: string }> };

export async function POST(request: NextRequest, { params }: Params) {
  const { clientId } = await params;
  const session = request.cookies.get("agency_session")?.value;
  const csrf = request.cookies.get("agency_csrf")?.value;

  if (!session) return NextResponse.redirect(new URL("/login", request.url), 303);
  if (!csrf || !ORG_ID) {
    return NextResponse.json({ detail: "Dashboard authentication is not configured" }, { status: 500 });
  }

  const form = await request.formData();
  const action = String(form.get("action") ?? "");
  const payloadClient = String(form.get("client_id") ?? "");
  if (payloadClient !== clientId) {
    return NextResponse.json({ detail: "client_id mismatch" }, { status: 400 });
  }

  const base = { org_id: ORG_ID, client_id: clientId };
  let path = "";
  let payload: Record<string, unknown> = base;

  switch (action) {
    case "approve-facts":
      path = "/v1/approvals/facts";
      break;
    case "research":
      path = "/v1/research";
      payload = { ...base, provider: "mock" };
      break;
    case "approve-research":
      path = "/v1/research/approve";
      payload = { ...base, artifact_id: String(form.get("artifact_id") ?? ""), approved_by: "dashboard", feedback: null };
      break;
    case "generate-content":
      path = "/v1/content";
      payload = { ...base, mode: "llm", provider: String(form.get("provider") ?? "mock") };
      break;
    case "approve-content":
      path = "/v1/content/approve";
      payload = { ...base, artifact_id: String(form.get("artifact_id") ?? ""), approved_by: "dashboard", feedback: null };
      break;
    case "design":
      path = "/v1/design";
      payload = {
        ...base,
        content_artifact_id: String(form.get("artifact_id") ?? ""),
        preset_id: "health",
        template_version: "1.0.0",
      };
      break;
    case "build":
      path = "/v1/builds/site";
      payload = {
        ...base,
        content_artifact_id: String(form.get("content_artifact_id") ?? ""),
        design_artifact_id: String(form.get("design_artifact_id") ?? ""),
      };
      break;
    case "approve-publish":
      path = "/v1/publish/approve";
      payload = {
        ...base,
        build_artifact_id: String(form.get("artifact_id") ?? ""),
        approved_by: "dashboard",
        feedback: null,
      };
      break;
    case "preview": {
      const siteVersionId = String(form.get("site_version_id") ?? "");
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(siteVersionId)) {
        return NextResponse.json({ detail: "Invalid site_version_id" }, { status: 400 });
      }
      path = "/v1/deploys/preview";
      payload = { ...base, site_version_id: siteVersionId, provider: "local_static" };
      break;
    }
    case "rollback": {
      const buildHash = String(form.get("build_hash") ?? "").toLowerCase();
      if (!/^[a-f0-9]{64}$/.test(buildHash)) {
        return NextResponse.json({ detail: "Invalid build_hash" }, { status: 400 });
      }
      path = "/v1/deploys/rollback";
      payload = { ...base, build_hash: buildHash };
      break;
    }
    case "publish":
      path = "/v1/deploys/publish";
      payload = {
        ...base,
        site_version_id: String(form.get("site_version_id") ?? ""),
      };
      break;
    default:
      return NextResponse.json({ detail: "Unknown workflow action" }, { status: 400 });
  }

  const upstream = await fetch(`${API_BASE_URL}${path}`, {
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
    const detail = (await upstream.text()).slice(0, 500);
    const target = new URL(`/clients/${clientId}`, request.url);
    target.searchParams.set("error", detail || "Workflow action failed");
    return NextResponse.redirect(target, 303);
  }

  const target = new URL(`/clients/${clientId}`, request.url);
  target.searchParams.set("result", action);
  return NextResponse.redirect(target, 303);
}
