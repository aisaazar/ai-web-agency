import { fetchAuditLog } from "../../lib/data";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const rows = await fetchAuditLog();
  return <>
    <div className="topbar"><div><div className="eyebrow">Governance</div><h1>Audit log</h1></div><div className="row"><span className="muted">{rows.length} recent events</span></div></div>
    <section className="card"><table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Entity</th><th>IP</th></tr></thead><tbody>
      {rows.map((event) => <tr key={event.id}><td>{event.createdAt}</td><td>{event.actor}</td><td><span className="badge">{event.action}</span></td><td>{event.entityType} / {event.entityId}</td><td>{event.ip ?? "—"}</td></tr>)}
      {rows.length === 0 ? <tr><td colSpan={5} className="muted">No audit events available for this organisation.</td></tr> : null}
    </tbody></table></section>
  </>;
}
