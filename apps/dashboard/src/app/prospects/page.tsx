import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";
const API_BASE_URL =
  process.env.AGENCY_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000";
const ORG_ID = process.env.AGENCY_ORG_ID;

type Prospect = {
  id: string;
  name: string;
  category: string;
  city: string | null;
  country: string;
  website_url: string | null;
  source_url: string | null;
  website_status: string;
  fit_score: number;
  opportunity_score: number;
  status: string;
  notes: string | null;
};

async function fetchProspects(): Promise<Prospect[]> {
  const session = (await cookies()).get("agency_session")?.value;
  if (!session) redirect("/login");
  if (!ORG_ID) throw new Error("AGENCY_ORG_ID is required for prospect access");
  const response = await fetch(
    API_BASE_URL + "/v1/prospects?org_id=" + encodeURIComponent(ORG_ID),
    { cache: "no-store", headers: { Cookie: "agency_session=" + session } },
  );
  if (response.status === 401) redirect("/login");
  if (!response.ok) throw new Error("Prospect API request failed: " + response.status);
  return response.json() as Promise<Prospect[]>;
}

export default async function ProspectsPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; result?: string }>;
}) {
  const query = await searchParams;
  const rows = await fetchProspects();
  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Acquisition</div>
          <h1>Prospect Workspace</h1>
          <div className="muted">
            Prioritize legitimate public business prospects before they enter client intake.
          </div>
        </div>
        <Link className="button" href="/prospects/new">Add prospect</Link>
      </div>
      {query.error ? <p className="error">{query.error}</p> : null}
      {query.result ? <p className="success">{query.result}</p> : null}
      <section className="card">
        <table>
          <thead>
            <tr><th>Prospect</th><th>Website</th><th>Opportunity</th><th>Fit</th><th>Status</th><th>Next step</th></tr>
          </thead>
          <tbody>

            {rows.map((p) => (
              <tr key={p.id}>
                <td>
                  <strong>{p.name}</strong>
                  <div className="muted">
                    {[p.category, p.city, p.country].filter(Boolean).join(" · ")}
                  </div>
                </td>
                <td>
                  {p.website_status === "missing"
                    ? <span className="badge">No website</span>
                    : p.website_status === "poor"
                      ? <span className="badge">Needs work</span>
                      : <span className="muted">{p.website_status}</span>}
                </td>
                <td><strong>{p.opportunity_score}/100</strong></td>
                <td>{p.fit_score}/60</td>
                <td><span className="badge">{p.status}</span></td>
                <td>
                  {p.status === "converted" || p.status === "dismissed"
                    ? <span className="muted">Closed</span>
                    : (
                      <div className="row">
                        <Link
                          className="button secondaryButton"
                          href={"/clients/new?client_name=" + encodeURIComponent(p.name) +
                            "&category=" + encodeURIComponent(p.category) +
                            "&existing_url=" + encodeURIComponent(p.website_url ?? "")}
                        >
                          Create intake
                        </Link>
                        {p.source_url
                          ? <a className="button secondaryButton" href={p.source_url} target="_blank" rel="noreferrer">Source</a>
                          : null}
                        <form action={"/api/prospects/" + p.id + "/status"} method="post" className="row">
                          <select name="status" defaultValue={p.status} aria-label={"Status for " + p.name}>
                            <option value="new">New</option>
                            <option value="contacted">Contacted</option>
                            <option value="qualified">Qualified</option>
                            <option value="converted">Converted</option>
                            <option value="dismissed">Dismissed</option>
                          </select>
                          <input name="note" placeholder="Optional note" aria-label={"Note for " + p.name} maxLength={2000} />
                          <button className="button secondaryButton" type="submit">Update</button>
                        </form>
                      </div>
                    )}
                </td>
              </tr>
            ))}

            {rows.length === 0
              ? <tr>
                  <td colSpan={6} className="muted">
                    No prospects yet. Add public research results and the workspace will prioritize them deterministically.
                  </td>
                </tr>
              : null}
          </tbody>
        </table>
      </section>
    </>
  );
}
