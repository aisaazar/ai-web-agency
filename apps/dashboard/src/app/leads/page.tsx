import Link from "next/link";
import { fetchDashboard } from "../../lib/data";

export const dynamic = "force-dynamic";

const ORG_ID = process.env.AGENCY_ORG_ID;

type Props = {
  searchParams: Promise<{ result?: string; error?: string }>;
};

const statuses = ["new", "contacted", "qualified", "won", "lost"] as const;

export default async function LeadsPage({ searchParams }: Props) {
  const query = await searchParams;
  const dashboard = await fetchDashboard();
  const rows = await dashboard.leads();
  const exportUrl = ORG_ID ? "/api/leads/export" : null;

  return <>
    <div className="topbar"><div><div className="eyebrow">Demand</div><h1>Lead Inbox</h1></div><div className="row"><span className="muted">Live API data</span>{exportUrl ? <a className="button" href={exportUrl}>Export CSV</a> : null}</div></div>
    {query.error ? <p className="error">{query.error}</p> : null}
    {query.result ? <p className="success">Lead updated: {query.result.replace("lead-", "")}</p> : null}
    <section className="card"><table><thead><tr><th>Lead</th><th>Email</th><th>Client</th><th>Status</th><th>Received</th><th>Update</th></tr></thead><tbody>
      {rows.map((lead) => <tr key={lead.id}><td><strong>{lead.name}</strong></td><td>{lead.email}</td><td>{lead.client}</td><td><span className="badge">{lead.status}</span></td><td>{lead.createdAt}</td><td>{lead.status === "spam" ? <span className="muted">Blocked</span> : <form className="statusForm" action={`/api/leads/${lead.id}/status`} method="post"><select name="status" defaultValue={lead.status}>{statuses.map((status) => <option key={status} value={status}>{status}</option>)}</select><button className="button" type="submit">Save</button></form>}</td></tr>)}
    </tbody></table></section>
  </>;
}