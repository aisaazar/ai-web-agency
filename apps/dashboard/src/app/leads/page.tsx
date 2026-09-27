import { fetchDashboard } from "../../lib/data";

export default async function LeadsPage() {
  const dashboard = await fetchDashboard();
  const rows = await dashboard.leads();
  return <><div className="topbar"><div><div className="eyebrow">Demand</div><h1>Lead Inbox</h1></div><span className="muted">Live API data</span></div>
    <section className="card"><table><thead><tr><th>Lead</th><th>Client</th><th>Status</th><th>Received</th></tr></thead><tbody>
      {rows.map(x=><tr key={x.id}><td><strong>{x.name}</strong></td><td>{x.client}</td><td><span className="badge">{x.status}</span></td><td>{x.createdAt}</td></tr>)}
    </tbody></table></section></>;
}
