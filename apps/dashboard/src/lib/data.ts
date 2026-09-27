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
  status: "new" | "contacted" | "qualified" | "won" | "lost";
  createdAt: string;
}

export interface DashboardDataAdapter {
  clients(): Promise<DashboardClient[]>;
  artifacts(): Promise<DashboardArtifact[]>;
  deployments(): Promise<DashboardDeployment[]>;
  leads(): Promise<DashboardLead[]>;
}
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

export async function fetchDashboard(): Promise<DashboardDataAdapter> {
  const query = ORG_ID ? `?org_id=${encodeURIComponent(ORG_ID)}` : "";
  const response = await fetch(`${API_BASE_URL}/v1/dashboard${query}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Dashboard API request failed: ${response.status}`);
  }

  const data = await response.json() as {
    clients: DashboardClient[];
    artifacts: DashboardArtifact[];
    deployments: DashboardDeployment[];
    leads: DashboardLead[];
  };

  return {
    clients: async () => data.clients,
    artifacts: async () => data.artifacts,
    deployments: async () => data.deployments,
    leads: async () => data.leads,
  };
}
