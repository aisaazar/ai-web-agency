import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export type PipelineState =
  | "INTAKE" | "FACTS_EXTRACTED" | "FACTS_APPROVED"
  | "RESEARCHING" | "RESEARCH_COMPLETE" | "RESEARCH_APPROVED"
  | "CONTENT_GENERATING" | "CONTENT_COMPLETE" | "CONTENT_APPROVED"
  | "DESIGNING" | "DESIGN_COMPLETE" | "DESIGN_APPROVED"
  | "BUILDING" | "BUILD_COMPLETE" | "BUILD_FAILED"
  | "PREVIEW_READY" | "PREVIEW_APPROVED"
  | "PUBLISHING" | "LIVE" | "MAINTENANCE" | "FAILED";

export interface DashboardClient {
  id: string;
  name: string;
  category: string;
  state: PipelineState;
  updatedAt: string;
}

export interface DashboardArtifact {
  id: string;
  type: string;
  revision: number;
  status: "approved" | "active" | "archived" | "pending";
  buildHash?: string;
}

export interface DashboardDeployment {
  id: string;
  siteVersionId: string;
  client: string;
  provider: string;
  environment: "preview" | "production" | string;
  status: "live" | "preview" | "failed" | "superseded";
  url: string;
}

export interface DashboardLead {
  id: string;
  client: string;
  name: string;
  email: string;
  status: "new" | "contacted" | "qualified" | "won" | "lost" | "spam";
  createdAt: string;
}

export interface DashboardDataAdapter {
  clients(): Promise<DashboardClient[]>;
  artifacts(): Promise<DashboardArtifact[]>;
  deployments(): Promise<DashboardDeployment[]>;
  leads(): Promise<DashboardLead[]>;
}

export interface DashboardLLMCost {
  orgId: string;
  budgetMicros: number;
  spentMicros: number;
  clients: Array<{
    clientId: string;
    clientName: string;
    budgetMicros: number;
    spentMicros: number;
  }>;
}

export interface DashboardAuditEvent {
  id: string;
  actor: string;
  action: string;
  entityType: string;
  entityId: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  ip?: string | null;
  createdAt: string;
}

export interface DashboardClientFact {
  id: string;
  key: string;
  value: string;
  valueType: string;
  sourceKind: string;
  sourceRef?: string;
  confidence?: number;
  status: string;
  approvedBy?: string;
  createdAt: string;
}

export interface DashboardClientDetailArtifact {
  id: string;
  type: string;
  revision: number;
  status: string;
  buildHash?: string;
  updatedAt: string;
}

export interface DashboardApproval {
  id: string;
  artifactId: string;
  gate: string;
  decision: string;
  feedback?: string;
  approvedBy?: string;
  createdAt: string;
}

export interface DashboardSiteVersion {
  id: string;
  buildHash: string;
  contentArtifactId: string;
  templateVersion: string;
  designPresetId: string;
  createdAt: string;
}

export interface DashboardClientDetail extends DashboardClient {
  liveUrl?: string;
  currentBuildHash?: string;
  facts: DashboardClientFact[];
  artifacts: DashboardClientDetailArtifact[];
  approvals: DashboardApproval[];
  siteVersions: DashboardSiteVersion[];
  deployments: DashboardDeployment[];
}
const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

type DashboardOverview = {
  clients: Array<{
    id: string;
    name: string;
    category: string;
    state: PipelineState;
    updated_at: string;
  }>;
  artifacts: Array<{
    id: string;
    type: string;
    revision: number;
    status: string;
    build_hash?: string | null;
  }>;
  deployments: Array<{
    id: string;
    site_version_id: string;
    client: string;
    provider: string;
    environment: string;
    status: string;
    url?: string | null;
  }>;
  leads: Array<{
    id: string;
    client: string;
    name: string;
    status: DashboardLead["status"];
    email: string;
    received_at: string;
  }>;
};

export async function fetchClientDetail(clientId: string): Promise<DashboardClientDetail> {
  const sessionCookie = (await cookies()).get("agency_session")?.value;
  if (!sessionCookie) {
    redirect("/login");
  }
  if (!ORG_ID) {
    throw new Error("AGENCY_ORG_ID is required for dashboard API access");
  }

  const response = await fetch(
    `${API_BASE_URL}/v1/dashboard/clients/${encodeURIComponent(clientId)}?org_id=${encodeURIComponent(ORG_ID)}`,
    {
      cache: "no-store",
      headers: { Cookie: `agency_session=${sessionCookie}` },
    },
  );

  if (response.status === 401) {
    redirect("/login");
  }
  if (!response.ok) {
    throw new Error(`Client detail request failed: ${response.status}`);
  }

  const data = await response.json() as {
    client: {
      id: string;
      name: string;
      category: string;
      state: PipelineState;
      updated_at: string;
      live_url?: string | null;
      current_build_hash?: string | null;
    };
    facts: Array<{
      id: string;
      key: string;
      value: string;
      value_type: string;
      source_kind: string;
      source_ref?: string | null;
      confidence?: number | null;
      status: string;
      approved_by?: string | null;
      created_at: string;
    }>;
    artifacts: Array<{
      id: string;
      type: string;
      revision: number;
      status: string;
      build_hash?: string | null;
      updated_at: string;
    }>;
    approvals: Array<{
      id: string;
      artifact_id: string;
      gate: string;
      decision: string;
      feedback?: string | null;
      approved_by?: string | null;
      created_at: string;
    }>;
    site_versions: Array<{
      id: string;
      build_hash: string;
      content_artifact_id: string;
      template_version: string;
      design_preset_id: string;
      created_at: string;
    }>;
    deployments: Array<{
      id: string;
      site_version_id: string;
      client: string;
      provider: string;
      environment: string;
      status: string;
      url?: string | null;
    }>;
  };

  return {
    id: data.client.id,
    name: data.client.name,
    category: data.client.category,
    state: data.client.state,
    updatedAt: data.client.updated_at,
    liveUrl: data.client.live_url ?? undefined,
    currentBuildHash: data.client.current_build_hash ?? undefined,
    facts: data.facts.map((item) => ({
      id: item.id,
      key: item.key,
      value: item.value,
      valueType: item.value_type,
      sourceKind: item.source_kind,
      sourceRef: item.source_ref ?? undefined,
      confidence: item.confidence ?? undefined,
      status: item.status,
      approvedBy: item.approved_by ?? undefined,
      createdAt: item.created_at,
    })),
    artifacts: data.artifacts.map((item) => ({
      id: item.id,
      type: item.type,
      revision: item.revision,
      status: item.status,
      buildHash: item.build_hash ?? undefined,
      updatedAt: item.updated_at,
    })),
    approvals: data.approvals.map((item) => ({
      id: item.id,
      artifactId: item.artifact_id,
      gate: item.gate,
      decision: item.decision,
      feedback: item.feedback ?? undefined,
      approvedBy: item.approved_by ?? undefined,
      createdAt: item.created_at,
    })),
    siteVersions: data.site_versions.map((item) => ({
      id: item.id,
      buildHash: item.build_hash,
      contentArtifactId: item.content_artifact_id,
      templateVersion: item.template_version,
      designPresetId: item.design_preset_id,
      createdAt: item.created_at,
    })),
    deployments: data.deployments.map((item) => ({
      id: item.id,
      siteVersionId: item.site_version_id,
      client: item.client,
      provider: item.provider,
      environment: item.environment,
      status: item.status === "live"
        ? "live"
        : item.status === "failed"
          ? "failed"
          : item.status === "superseded"
            ? "superseded"
            : "preview",
      url: item.url ?? "",
    })),
  };
}

export async function fetchDeploymentLogs(clientId: string, deployId: string): Promise<string> {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get("agency_session")?.value;
  const csrfCookie = cookieStore.get("agency_csrf")?.value;
  if (!sessionCookie) redirect("/login");
  if (!csrfCookie) throw new Error("agency_csrf cookie is required for dashboard API access");
  if (!ORG_ID) throw new Error("AGENCY_ORG_ID is required for dashboard API access");

  const response = await fetch(API_BASE_URL + "/v1/deploys/logs", {
    method: "POST",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Cookie: "agency_session=" + sessionCookie + "; agency_csrf=" + csrfCookie,
      "X-CSRF-Token": csrfCookie,
    },
    body: JSON.stringify({ org_id: ORG_ID, client_id: clientId, deploy_id: deployId }),
  });

  if (response.status === 401) redirect("/login");
  if (!response.ok) throw new Error("Deployment logs request failed: " + response.status);

  const data = await response.json() as { logs?: string };
  return data.logs ?? "";
}


export async function fetchLLMCost(): Promise<DashboardLLMCost> {
  const sessionCookie = (await cookies()).get("agency_session")?.value;
  if (!sessionCookie) redirect("/login");
  if (!ORG_ID) throw new Error("AGENCY_ORG_ID is required for dashboard API access");
  const response = await fetch(
    `${API_BASE_URL}/v1/dashboard/llm-cost?org_id=${encodeURIComponent(ORG_ID)}`,
    { cache: "no-store", headers: { Cookie: `agency_session=${sessionCookie}` } },
  );
  if (response.status === 401) redirect("/login");
  if (!response.ok) throw new Error(`LLM cost request failed: ${response.status}`);
  const data = await response.json() as {
    org_id: string;
    budget_micros: number;
    spent_micros: number;
    clients: Array<{ client_id: string; client_name: string; budget_micros: number; spent_micros: number }>;
  };
  return {
    orgId: data.org_id,
    budgetMicros: data.budget_micros,
    spentMicros: data.spent_micros,
    clients: data.clients.map((item) => ({
      clientId: item.client_id,
      clientName: item.client_name,
      budgetMicros: item.budget_micros,
      spentMicros: item.spent_micros,
    })),
  };
}

export async function fetchAuditLog(limit = 50): Promise<DashboardAuditEvent[]> {
  const sessionCookie = (await cookies()).get("agency_session")?.value;
  if (!sessionCookie) redirect("/login");
  if (!ORG_ID) throw new Error("AGENCY_ORG_ID is required for dashboard API access");
  const response = await fetch(
    `${API_BASE_URL}/v1/audit?org_id=${encodeURIComponent(ORG_ID)}&limit=${encodeURIComponent(limit)}`,
    { cache: "no-store", headers: { Cookie: `agency_session=${sessionCookie}` } },
  );
  if (response.status === 401) redirect("/login");
  if (response.status === 403) return [];
  if (!response.ok) throw new Error(`Audit request failed: ${response.status}`);
  const data = await response.json() as Array<{
    id: string; actor: string; action: string; entity_type: string; entity_id: string;
    before?: Record<string, unknown> | null; after?: Record<string, unknown> | null;
    ip?: string | null; created_at: string;
  }>;
  return data.map((item) => ({
    id: item.id,
    actor: item.actor,
    action: item.action,
    entityType: item.entity_type,
    entityId: item.entity_id,
    before: item.before,
    after: item.after,
    ip: item.ip,
    createdAt: item.created_at,
  }));
}

export async function fetchDashboard(): Promise<DashboardDataAdapter> {
  const sessionCookie = (await cookies()).get("agency_session")?.value;
  if (!sessionCookie) {
    redirect("/login");
  }
  if (!ORG_ID) {
    throw new Error("AGENCY_ORG_ID is required for dashboard API access");
  }
  const response = await fetch(
    `${API_BASE_URL}/v1/dashboard/overview?org_id=${encodeURIComponent(ORG_ID)}`,
    {
      cache: "no-store",
      headers: sessionCookie ? { Cookie: `agency_session=${sessionCookie}` } : undefined,
    },
  );

  if (response.status === 401) {
    redirect("/login");
  }
  if (!response.ok) {
    throw new Error(`Dashboard API request failed: ${response.status}`);
  }

  const data = await response.json() as DashboardOverview;

  return {
    clients: async () =>
      data.clients.map((client) => ({
        id: client.id,
        name: client.name,
        category: client.category,
        state: client.state,
        updatedAt: client.updated_at,
      })),
    artifacts: async () =>
      data.artifacts.map((artifact) => ({
        id: artifact.id,
        type: artifact.type,
        revision: artifact.revision,
        status: artifact.status === "active"
          ? "active"
          : artifact.status === "archived"
            ? "archived"
            : "pending",
        buildHash: artifact.build_hash ?? undefined,
      })),
    deployments: async () =>
      data.deployments.map((deployment) => ({
        id: deployment.id,
        siteVersionId: deployment.site_version_id,
        client: deployment.client,
        provider: deployment.provider,
        environment: deployment.environment,
        status: deployment.status === "live"
          ? "live"
          : deployment.status === "failed"
            ? "failed"
            : deployment.status === "superseded"
              ? "superseded"
              : "preview",
        url: deployment.url ?? "",
      })),
    leads: async () =>
      data.leads.map((lead) => ({
        id: lead.id,
        client: lead.client,
        name: lead.name,
        email: lead.email,
        status: lead.status,
        createdAt: lead.received_at,
      })),
  };
}
