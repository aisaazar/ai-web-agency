import { fetchLLMCost } from "../../lib/data";

export const dynamic = "force-dynamic";

function eur(micros: number): string {
  return new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR" }).format(micros / 1_000_000);
}

export default async function CostsPage() {
  const report = await fetchLLMCost();
  const remaining = Math.max(0, report.budgetMicros - report.spentMicros);
  return <>
    <div className="topbar"><div><div className="eyebrow">Operations</div><h1>LLM costs</h1></div><div className="row"><span className="muted">Live API data</span></div></div>
    <div className="grid">
      <section className="card"><div className="muted">Organisation budget</div><div className="kpi">{eur(report.budgetMicros)}</div></section>
      <section className="card"><div className="muted">Spent</div><div className="kpi">{eur(report.spentMicros)}</div></section>
      <section className="card"><div className="muted">Remaining</div><div className="kpi">{eur(remaining)}</div></section>
    </div>
    <section className="card section"><h2 className="sectionTitle">Spend by client</h2>
      <table><thead><tr><th>Client</th><th>Budget</th><th>Spent</th><th>Remaining</th></tr></thead><tbody>
        {report.clients.map((item) => {
          const left = Math.max(0, item.budgetMicros - item.spentMicros);
          return <tr key={item.clientId}><td>{item.clientName}</td><td>{eur(item.budgetMicros)}</td><td>{eur(item.spentMicros)}</td><td>{eur(left)}</td></tr>;
        })}
        {report.clients.length === 0 ? <tr><td colSpan={4} className="muted">No client spend recorded yet.</td></tr> : null}
      </tbody></table>
    </section>
  </>;
}
