import Link from "next/link";

export default function NotFound() {
  return (
    <section className="card">
      <div className="eyebrow">Not found</div>
      <h1>Nothing here</h1>
      <p className="muted">
        This record does not exist, or it is not available for the organisation this dashboard is
        configured for.
      </p>
      <p>
        <Link className="button" href="/">
          Back to overview
        </Link>
      </p>
    </section>
  );
}
