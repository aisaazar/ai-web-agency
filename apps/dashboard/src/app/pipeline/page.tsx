import Link from "next/link";
import { fetchDashboard } from "../../lib/data";

export const dynamic = "force-dynamic";


export default async function PipelinePage() {
  const dashboard = await fetchDashboard();
  const rows = await dashboard.clients();
  return <><div className="topbar"><div><div className="eyebrow">Workflow</div><h1>Pipeline</h1></div><span className="muted">Approval-driven state machine</span></div>
    <div className="grid">{rows.map(x=><section className="card" key={x.id}><div className="row"><div><strong><Link href={`/clients/${x.id}`}>{x.name}</Link></strong><div className="muted">{x.category}</div></div><span className="badge">{x.state}</span></div><p className="muted">Human approval is required at Facts, Research, Content and Publish gates.</p><p><Link className="button secondaryButton" href={`/clients/${x.id}`}>Open control center</Link></p></section>)}
      {rows.length === 0 ? <section className="card"><p className="muted">No clients in the pipeline yet. <Link href="/clients/new">Create a client</Link> to start the approval-driven workflow.</p></section> : null}
    </div></>;
}