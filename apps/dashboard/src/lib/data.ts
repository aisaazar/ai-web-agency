export type PipelineState =
  | "INTAKE" | "FACTS_APPROVED" | "RESEARCH_APPROVED" | "CONTENT_APPROVED"
  | "DESIGN_APPROVED" | "PREVIEW_READY" | "PREVIEW_APPROVED" | "LIVE";

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
  status: "approved" | "active" | "pending";
  buildHash?: string;
}

export interface DashboardDeployment {
  id: string;
  client: string;
  provider: string;
  status: "live" | "preview" | "failed";
  url: string;
}

export interface DashboardLead {
  id: string;
  client: string;
  name: string;
  email: string;
  status: "new" | "contacted" | "qualified" | "won" | "lost";
  createdAt: string;
}

export interface DashboardDataAdapter {
  clients(): Promise<DashboardClient[]>;
  artifacts(): Promise<DashboardArtifact[]>;
  deployments(): Promise<DashboardDeployment[]>;
  leads(): Promise<DashboardLead[]>;
}
export const mockDashboardData: DashboardDataAdapter = {
  clients: async () => [
    {
      id: "client-1",
      name: "Zahnbalance Nürnberg",
      category: "dental",
      state: "PREVIEW_READY",
      updatedAt: "2026-09-27",
    },
    {
      id: "client-2",
      name: "Nordlicht Physiotherapie",
      category: "health",
      state: "CONTENT_APPROVED",
      updatedAt: "2026-09-26",
    },
  ],
  artifacts: async () => [
    { id: "art-1", type: "business_facts", revision: 1, status: "approved" },
    { id: "art-2", type: "content_model", revision: 3, status: "approved" },
    { id: "art-3", type: "site_build", revision: 1, status: "active", buildHash: "8e7f…a91c" },
  ],
  deployments: async () => [
    {
      id: "dep-1",
      client: "Zahnbalance Nürnberg",
      provider: "local_static",
      status: "preview",
      url: "local://8e7f…a91c",
    },
  ],
  leads: async () => [
    {
      id: "lead-1",
      client: "Zahnbalance Nürnberg",
      name: "Maria K.",
      email: "maria@example.com",
      status: "new",
      createdAt: "2026-09-27 10:22",
    },
  ],
};
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

export async function fetchDashboard(): Promise<DashboardDataAdapter> {
  if (!ORG_ID) {
    return mockDashboardData;
  }

  const response = await fetch(
    `${API_BASE_URL}/v1/dashboard/overview?org_id=${encodeURIComponent(ORG_ID)}`,
    { cache: "no-store" },
  );

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
        status: artifact.status === "active" ? "active" : "pending",
        buildHash: artifact.build_hash ?? undefined,
      })),
    deployments: async () =>
      data.deployments.map((deployment) => ({
        id: deployment.id,
        client: deployment.client,
        provider: deployment.provider,
        status: deployment.status === "live"
          ? "live"
          : deployment.status === "failed"
            ? "failed"
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
