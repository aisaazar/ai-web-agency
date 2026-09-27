import { fetchDashboard } from "../../lib/data";

export const dynamic = "force-dynamic";


export default async function ClientsPage() {
  const dashboard = await fetchDashboard();
  const rows = await dashboard.clients();
  return <><div className="topbar"><div><div className="eyebrow">Accounts</div><h1>Clients</h1></div><span className="muted">{rows.length} clients</span></div>
    <section className="card"><table><thead><tr><th>Name</th><th>Category</th><th>Pipeline</th><th>Updated</th></tr></thead><tbody>
      {rows.map(x=><tr key={x.id}><td><strong>{x.name}</strong></td><td>{x.category}</td><td><span className="badge">{x.state}</span></td><td>{x.updatedAt}</td></tr>)}
    </tbody></table></section></>;
}