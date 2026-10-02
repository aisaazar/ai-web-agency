import Link from "next/link";

export const dynamic = "force-dynamic";

export default function NewProspectPage() {
  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Acquisition</div>
          <h1>Add prospect</h1>
        </div>
        <Link className="button secondaryButton" href="/prospects">Back</Link>
      </div>
      <section className="card">
        <p className="muted">
          Enter legitimate public business information. The score is deterministic:
          missing or weak websites and reachable business contact channels increase opportunity.
        </p>
        <form action="/api/prospects" method="post" className="intakeForm">
          <label>Business name<input name="name" required maxLength={200} /></label>
          <div className="formGrid">
            <label>Category<input name="category" required maxLength={100} placeholder="dental" /></label>
            <label>City<input name="city" maxLength={120} /></label>
          </div>
          <div className="formGrid">
            <label>Website URL<input name="website_url" type="url" /></label>
            <label>Website status
              <select name="website_status" defaultValue="unknown">
                <option value="missing">Missing</option>
                <option value="poor">Needs work</option>
                <option value="unknown">Unknown</option>
                <option value="good">Good</option>
              </select>
            </label>
          </div>
          <div className="formGrid">
            <label>Contactability
              <select name="contactability" defaultValue="unknown">
                <option value="email+phone">Email + phone</option>
                <option value="email">Email</option>
                <option value="phone">Phone</option>
                <option value="unknown">Unknown</option>
              </select>
            </label>
            <label>Source type
              <select name="source_kind" defaultValue="public_directory">
                <option value="public_directory">Public directory</option>
                <option value="search">Search</option>
                <option value="manual">Manual research</option>
              </select>
            </label>
          </div>
          <label>Public source URL<input name="source_url" type="url" /></label>
          <label>Notes
            <textarea name="notes" rows={5} maxLength={4000}
              placeholder="Why this business is a plausible website prospect." />
          </label>
          <div className="row formActions">
            <Link className="button secondaryButton" href="/prospects">Cancel</Link>
            <button className="button" type="submit">Add & prioritize</button>
          </div>
        </form>
      </section>
    </>
  );
}
