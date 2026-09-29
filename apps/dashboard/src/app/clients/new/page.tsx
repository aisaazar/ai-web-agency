import Link from "next/link";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{ error?: string }>;
};

export default async function NewClientPage({ searchParams }: Props) {
  const query = await searchParams;

  return (
    <>
      <div className="topbar">
        <div>
          <div className="eyebrow">Accounts</div>
          <h1>New client</h1>
        </div>
        <Link className="button secondaryButton" href="/clients">Back</Link>
      </div>
      {query.error ? <p className="error">{query.error}</p> : null}
      <section className="card">
        <p className="muted">Start the approved intake workflow. Add the initial business facts now so the client can move into Facts approval immediately.</p>
        <form action="/api/intake" method="post" className="intakeForm">
          <label>Client name<input name="client_name" required maxLength={200} /></label>
          <label>Client slug<input name="client_slug" required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" maxLength={120} /></label>
          <label>Category<select name="category" defaultValue="dental"><option value="dental">Dental</option><option value="health">Health</option><option value="corporate">Corporate</option></select></label>
          <div className="formGrid">
            <label>Jurisdiction<input name="jurisdiction" defaultValue="DE" required maxLength={8} /></label>
            <label>Locale<input name="locale" defaultValue="de-DE" required maxLength={16} /></label>
          </div>
          <label>Initial business facts
            <textarea name="facts" required rows={8} placeholder={"One fact per line, in key=value form.\nbrand_name=Praxis Beispiel\nphone=+49 911 123456\ncity=Nürnberg"} />
            <span className="muted">At least one fact is required. These facts enter the Facts approval gate as proposed data.</span>
          </label>
          <label>Existing website URL<input name="existing_url" type="url" placeholder="https://example.de" /></label>
          <div className="row formActions">
            <Link className="button secondaryButton" href="/clients">Cancel</Link>
            <button className="button" type="submit">Create client & start intake</button>
          </div>
        </form>
      </section>
    </>
  );
}
