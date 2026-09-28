import Link from "next/link";
import { fetchDashboard } from "../../lib/data";

export const dynamic = "force-dynamic";


export default async function ClientsPage() {
  const dashboard = await fetchDashboard();
  const rows = await dashboard.clients();
  return <><div className="topbar"><div><div className="eyebrow">Accounts</div><h1>Clients</h1></div><div className="row"><span className="muted">{rows.length} clients</span><Link className="button" href="/clients/new">New client</Link></div></div>
    <section className="card"><table><thead><tr><th>Name</th><th>Category</th><th>Pipeline</th><th>Updated</th></tr></thead><tbody>
      {rows.map(x=><tr key={x.id}><td><strong><Link href={`/clients/${x.id}`}>{x.name}</Link></strong></td><td>{x.category}</td><td><span className="badge">{x.state}</span></td><td>{x.updatedAt}</td></tr>)}
    </tbody></table></section></>;
}