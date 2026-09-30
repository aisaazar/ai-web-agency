import Link from "next/link";
import { fetchDashboard } from "../lib/data";

export const dynamic = "force-dynamic";


export default async function OverviewPage() {
  const dashboard = await fetchDashboard();
  const [clients, artifacts, deployments, leads] = await Promise.all([
    dashboard.clients(), dashboard.artifacts(), dashboard.deployments(), dashboard.leads(),
  ]);
  return <>
    <div className="topbar"><div><div className="eyebrow">Operations</div><h1>Agency Overview</h1></div><div className="muted">Live API data</div></div>
    <div className="grid kpis">
      {[
        ["Clients",clients.length],["Artifacts",artifacts.length],["Deployments",deployments.length],
        ["New leads",leads.filter(x=>x.status==="new").length],
      ].map(([label,value])=><div className="card" key={String(label)}><div className="muted">{label}</div><div className="kpi">{value}</div></div>)}
    </div>
    <div className="grid two section">
      <section className="card"><h2 className="sectionTitle">Pipeline attention</h2><div className="list">
        {clients.map(c=><div className="row" key={c.id}><div><strong><Link href={`/clients/${c.id}`}>{c.name}</Link></strong><div className="muted">{c.category}</div></div><span className="badge">{c.state}</span></div>)}
        {clients.length === 0 ? <p className="muted">No clients yet. <Link href="/clients/new">Create the first client</Link> to start the pipeline.</p> : null}
      </div></section>
      <section className="card"><h2 className="sectionTitle">Recent leads</h2><div className="list">
        {leads.map(l=><div className="row" key={l.id}><div><strong>{l.name}</strong><div className="muted">{l.client}</div></div><span className="badge">{l.status}</span></div>)}
        {leads.length === 0 ? <p className="muted">No leads captured yet.</p> : null}
      </div><p><Link className="button" href="/leads">Open lead inbox</Link></p></section>
    </div>
  </>;
}
