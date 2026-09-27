import { mockDashboardData } from "../../lib/data";

export default async function DeploymentsPage() {
  const rows = await mockDashboardData.deployments();
  return <><div className="topbar"><div><div className="eyebrow">Delivery</div><h1>Deployments</h1></div></div>
    <section className="card"><table><thead><tr><th>Client</th><th>Provider</th><th>Status</th><th>URL</th></tr></thead><tbody>
      {rows.map(x=><tr key={x.id}><td>{x.client}</td><td>{x.provider}</td><td><span className="badge">{x.status}</span></td><td>{x.url}</td></tr>)}
    </tbody></table></section></>;
}