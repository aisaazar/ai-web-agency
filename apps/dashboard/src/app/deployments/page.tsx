import { fetchDashboard } from "../../lib/data";

export const dynamic = "force-dynamic";


export default async function DeploymentsPage() {
  const dashboard = await fetchDashboard();
  const rows = await dashboard.deployments();
  return <><div className="topbar"><div><div className="eyebrow">Delivery</div><h1>Deployments</h1></div></div>
    <section className="card"><table><thead><tr><th>Client</th><th>Provider</th><th>Status</th><th>URL</th></tr></thead><tbody>
      {rows.map(x=><tr key={x.id}><td>{x.client}</td><td>{x.provider}</td><td><span className="badge">{x.status}</span></td><td>{x.url}</td></tr>)}
      {rows.length === 0 ? <tr><td colSpan={4} className="muted">No deployments yet. Approve a build and deploy a preview from a client page.</td></tr> : null}
    </tbody></table></section></>;
}