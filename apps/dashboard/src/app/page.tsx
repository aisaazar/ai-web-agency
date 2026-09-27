import Link from "next/link";
import { mockDashboardData } from "../lib/data";

export default async function OverviewPage() {
  const [clients, artifacts, deployments, leads] = await Promise.all([
    mockDashboardData.clients(), mockDashboardData.artifacts(),
    mockDashboardData.deployments(), mockDashboardData.leads(),
  ]);
  return <>
    <div className="topbar"><div><div className="eyebrow">Operations</div><h1>Agency Overview</h1></div><div className="muted">Local preview data</div></div>
    <div className="grid kpis">
      {[
        ["Clients",clients.length],["Artifacts",artifacts.length],["Deployments",deployments.length],
        ["New leads",leads.filter(x=>x.status==="new").length],
      ].map(([label,value])=><div className="card" key={String(label)}><div className="muted">{label}</div><div className="kpi">{value}</div></div>)}
    </div>
    <div className="grid two section">
      <section className="card"><h2 className="sectionTitle">Pipeline attention</h2><div className="list">
        {clients.map(c=><div className="row" key={c.id}><div><strong>{c.name}</strong><div className="muted">{c.category}</div></div><span className="badge">{c.state}</span></div>)}
      </div></section>
      <section className="card"><h2 className="sectionTitle">Recent leads</h2><div className="list">
        {leads.map(l=><div className="row" key={l.id}><div><strong>{l.name}</strong><div className="muted">{l.client}</div></div><span className="badge">{l.status}</span></div>)}
      </div><p><Link className="button" href="/leads">Open lead inbox</Link></p></section>
    </div>
  </>;
}
