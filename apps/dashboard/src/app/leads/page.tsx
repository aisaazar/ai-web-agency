import { fetchDashboard } from "../../lib/data";

export const dynamic = "force-dynamic";

const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

export default async function LeadsPage() {
  const dashboard = await fetchDashboard();
  const rows = await dashboard.leads();
  const exportUrl = ORG_ID
    ? `${API_BASE_URL}/v1/leads/export.csv?org_id=${encodeURIComponent(ORG_ID)}`
    : null;
  return <><div className="topbar"><div><div className="eyebrow">Demand</div><h1>Lead Inbox</h1></div><div className="row"><span className="muted">Live API data</span>{exportUrl && <a className="button" href={exportUrl}>Export CSV</a>}</div></div>
    <section className="card"><table><thead><tr><th>Lead</th><th>Email</th><th>Client</th><th>Status</th><th>Received</th></tr></thead><tbody>
      {rows.map(x=><tr key={x.id}><td><strong>{x.name}</strong></td><td>{x.email}</td><td>{x.client}</td><td><span className="badge">{x.status}</span></td><td>{x.createdAt}</td></tr>)}
    </tbody></table></section></>;
}
