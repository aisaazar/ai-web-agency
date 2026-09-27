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

const clients: DashboardClient[] = [
  { id: "client-1", name: "Zahnbalance Nürnberg", category: "dental", state: "PREVIEW_READY", updatedAt: "2026-09-27" },
  { id: "client-2", name: "Nordlicht Physiotherapie", category: "health", state: "CONTENT_APPROVED", updatedAt: "2026-09-26" },
];

const artifacts: DashboardArtifact[] = [
  { id: "art-1", type: "business_facts", revision: 1, status: "approved" },
  { id: "art-2", type: "content_model", revision: 3, status: "approved" },
  { id: "art-3", type: "site_build", revision: 1, status: "active", buildHash: "8e7f…a91c" },
];

const deployments: DashboardDeployment[] = [
  { id: "dep-1", client: "Zahnbalance Nürnberg", provider: "local_static", status: "preview", url: "local://8e7f…a91c" },
];

const leads: DashboardLead[] = [
  { id: "lead-1", client: "Zahnbalance Nürnberg", name: "Maria K.", status: "new", createdAt: "2026-09-27 10:22" },
];

export const mockDashboardData: DashboardDataAdapter = {
  async clients() { return clients; },
  async artifacts() { return artifacts; },
  async deployments() { return deployments; },
  async leads() { return leads; },
};
