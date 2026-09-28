import Link from "next/link";
import { fetchClientDetail, fetchDeploymentLogs } from "../../../../../lib/data";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ clientId: string; deployId: string }>;
};

export default async function DeploymentLogsPage({ params }: Props) {
  const { clientId, deployId } = await params;
  const [detail, logs] = await Promise.all([
    fetchClientDetail(clientId),
    fetchDeploymentLogs(clientId, deployId),
  ]);
  const deployment = detail.deployments.find((item) => item.id === deployId);

  if (!deployment) {
    throw new Error("Deployment not found for this client");
  }

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Delivery</div>
          <h1>Deployment logs</h1>
          <div className="muted">{detail.name} · {deployment.environment} · {deployment.provider}</div>
        </div>
        <Link className="button secondaryButton" href={`/clients/${clientId}`}>Back to client</Link>
      </div>

      <section className="card">
        <div className="grid two">
          <div><div className="muted">Status</div><div><span className="badge">{deployment.status}</span></div></div>
          <div><div className="muted">URL</div><div className="mono">{deployment.url || "—"}</div></div>
        </div>
      </section>
      <section className="card section">
        <h2 className="sectionTitle">Provider output</h2>
        <pre className="logBox">{logs || "No deployment logs returned."}</pre>
      </section>
    </>
  );
}
