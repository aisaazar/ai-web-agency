"use client";

const API_FAILURE =
  /request failed|failed to fetch|unavailable|econnrefused|etimedout|request timed out|internal server error|\b5\d\d\b/i;

/**
 * Client-side boundary for the whole dashboard.
 *
 * Server components in this app fetch from the agency API and throw on a non-2xx answer or an
 * unreachable API. Without a boundary that surfaces as a generic Next.js crash page; operators need
 * to know the difference between "the API is down" and "this view has a bug", and they need a retry.
 */
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const message = error.message || "The dashboard view could not be loaded.";
  const apiUnavailable = API_FAILURE.test(message);

  return (
    <section className="card">
      <div className="eyebrow">Operations</div>
      <h1>{apiUnavailable ? "Agency API unavailable" : "Dashboard error"}</h1>
      <p className="muted">
        {apiUnavailable
          ? "The dashboard could not reach the agency API. Check that the API is running and that AGENCY_API_URL points at it, then retry."
          : "This view could not be rendered. Retry, and check the API logs if it keeps failing."}
      </p>
      <p className="error">{message}</p>
      {error.digest ? <p className="muted mono">Reference: {error.digest}</p> : null}
      <div className="row formActions">
        <button className="button" type="button" onClick={reset}>
          Retry
        </button>
      </div>
    </section>
  );
}
