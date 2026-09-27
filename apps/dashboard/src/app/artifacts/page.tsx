import { fetchDashboard } from "../../lib/data";

export const dynamic = "force-dynamic";


export default async function ArtifactsPage() {
  const dashboard = await fetchDashboard();
  const rows = await dashboard.artifacts();
  return <><div className="topbar"><div><div className="eyebrow">Traceability</div><h1>Artifacts & Approvals</h1></div></div>
    <section className="card"><table><thead><tr><th>Type</th><th>Revision</th><th>Status</th><th>Build hash</th></tr></thead><tbody>
      {rows.map(x=><tr key={x.id}><td>{x.type}</td><td>{x.revision}</td><td><span className="badge">{x.status}</span></td><td>{x.buildHash ?? "—"}</td></tr>)}
    </tbody></table></section></>;
}