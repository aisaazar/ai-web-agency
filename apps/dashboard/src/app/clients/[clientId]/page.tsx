import Link from "next/link";
import { fetchClientDetail } from "../../../lib/data";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ clientId: string }>;
  searchParams: Promise<{ result?: string; error?: string }>;
};

const stages = [
  ["INTAKE", "Intake"], ["FACTS_EXTRACTED", "Facts review"], ["FACTS_APPROVED", "Facts approved"],
  ["RESEARCHING", "Research"], ["RESEARCH_COMPLETE", "Research review"], ["RESEARCH_APPROVED", "Research approved"],
  ["CONTENT_GENERATING", "Content"], ["CONTENT_COMPLETE", "Content review"], ["CONTENT_APPROVED", "Content approved"],
  ["DESIGNING", "Design"], ["DESIGN_APPROVED", "Design approved"], ["BUILDING", "Build"],
  ["BUILD_FAILED", "Build failed"], ["BUILD_COMPLETE", "Build complete"],
  ["PREVIEW_READY", "Preview review"], ["PREVIEW_APPROVED", "Preview approved"],
  ["PUBLISHING", "Publishing"], ["LIVE", "Live"], ["FAILED", "Failed"],
] as const;

function ActionForm({ action, clientId, hidden = {}, children }: {
  action: string; clientId: string; hidden?: Record<string, string>; children: React.ReactNode;
}) {
  return (
    <form action={`/api/clients/${clientId}/action`} method="post">
      <input type="hidden" name="action" value={action} />
      <input type="hidden" name="client_id" value={clientId} />
      {Object.entries(hidden).map(([name, value]) => <input key={name} type="hidden" name={name} value={value} />)}
      <button className="button" type="submit">{children}</button>
    </form>
  );
}

function findArtifact(detail: Awaited<ReturnType<typeof fetchClientDetail>>, type: string) {
  return detail.artifacts.find((item) => item.type === type);
}

export default async function ClientDetailPage({ params, searchParams }: Props) {
  const { clientId } = await params;
  const query = await searchParams;
  const detail = await fetchClientDetail(clientId);

  const research = findArtifact(detail, "research_report");
  const content = findArtifact(detail, "content_model");
  const design = findArtifact(detail, "design_plan");
  const build = findArtifact(detail, "site_build");
  const siteVersion = detail.siteVersions[0];
  const latestPreview = detail.deployments.find(
    (item) => item.environment === "preview" && item.siteVersionId === siteVersion?.id,
  );
  const latestProduction = detail.deployments.find(
    (item) => item.environment === "production",
  );
  const rollbackTargets = detail.siteVersions.filter(
    (item) => item.buildHash !== detail.currentBuildHash,
  );

  let action: React.ReactNode = null;
  switch (detail.state) {
    case "FACTS_EXTRACTED": action = <ActionForm action="approve-facts" clientId={clientId}>Approve facts</ActionForm>; break;
    case "FACTS_APPROVED": action = <ActionForm action="research" clientId={clientId}>Run research</ActionForm>; break;
    case "RESEARCH_COMPLETE":
      if (research) action = <ActionForm action="approve-research" clientId={clientId} hidden={{ artifact_id: research.id }}>Approve research</ActionForm>;
      break;
    case "RESEARCH_APPROVED":
      action = <ActionForm action="generate-content" clientId={clientId} hidden={{ provider: "local" }}>Generate content with local AI</ActionForm>;
      break;
    case "CONTENT_COMPLETE":
      if (content) action = <ActionForm action="approve-content" clientId={clientId} hidden={{ artifact_id: content.id }}>Approve content</ActionForm>;
      break;
    case "CONTENT_APPROVED":
      if (content) action = <ActionForm action="design" clientId={clientId} hidden={{ artifact_id: content.id }}>Create design</ActionForm>;
      break;
    case "DESIGN_APPROVED":
      if (content && design) action = <ActionForm action="build" clientId={clientId} hidden={{ content_artifact_id: content.id, design_artifact_id: design.id }}>Build site</ActionForm>;
      break;
    case "BUILD_FAILED":
      if (content && design) action = <ActionForm action="build" clientId={clientId} hidden={{ content_artifact_id: content.id, design_artifact_id: design.id }}>Retry failed build</ActionForm>;
      break;
    case "FAILED":
      action = <ActionForm action="generate-content" clientId={clientId} hidden={{ provider: "local" }}>Retry failed content generation</ActionForm>;
      break;
    case "PREVIEW_READY":
      if (build && siteVersion && !latestPreview) {
        action = <ActionForm action="preview" clientId={clientId} hidden={{ site_version_id: siteVersion.id }}>Deploy preview</ActionForm>;
      } else if (build) {
        action = <ActionForm action="approve-publish" clientId={clientId} hidden={{ artifact_id: build.id }}>Approve preview</ActionForm>;
      }
      break;
    case "PREVIEW_APPROVED":
      if (siteVersion) action = <ActionForm action="publish" clientId={clientId} hidden={{ site_version_id: siteVersion.id }}>Publish site</ActionForm>;
      break;
  }

  return <>
    <div className="topbar">
      <div><div className="eyebrow">Client Control Center</div><h1>{detail.name}</h1><div className="muted">{detail.category} · {detail.state}</div></div>
      <Link className="button secondaryButton" href="/clients">Back</Link>
    </div>
    {query.error ? <p className="error">{query.error}</p> : null}
    {query.result ? <p className="success">Action completed: {query.result.replaceAll("-", " ")}</p> : null}

    <section className="card">
      <div className="detailHeader">
        <div><div className="muted">Current pipeline state</div><div className="detailState">{detail.state}</div></div>
        {action ?? <span className="muted">No action available at this state.</span>}
      </div>
      <div className="stageGrid">
        {stages.map(([state, label]) => <div className={`stage ${state === detail.state ? "current" : ""}`} key={state}><span className="stageDot" aria-hidden="true" />{label}</div>)}
      </div>
    </section>

    <div className="grid two section">
      <section className="card"><h2 className="sectionTitle">Business facts</h2><div className="list">
        {detail.facts.map((fact) => <div className="row" key={fact.id}><div><strong>{fact.key}</strong><div className="muted">{fact.value}</div><div className="muted">{fact.sourceKind}{fact.sourceRef ? ` · ${fact.sourceRef}` : ""}{fact.confidence != null ? ` · confidence ${fact.confidence}` : ""}</div></div><span className="badge">{fact.status}</span></div>)}
        {detail.facts.length === 0 ? <p className="muted">No business facts yet. Add facts during client intake before approval.</p> : null}
      </div></section>
      <section className="card"><h2 className="sectionTitle">Artifacts</h2><div className="list">
        {detail.artifacts.map((item) => <div className="row" key={item.id}><div><strong>{item.type}</strong><div className="muted">Revision {item.revision}</div></div><span className="badge">{item.status}</span></div>)}
        {detail.artifacts.length === 0 ? <p className="muted">No artifacts yet.</p> : null}
      </div></section>
      <section className="card"><h2 className="sectionTitle">Approval trail</h2><div className="list">
        {detail.approvals.map((item) => <div className="row" key={item.id}><div><strong>{item.gate}</strong><div className="muted">{item.approvedBy ?? "—"}</div></div><span className="badge">{item.decision}</span></div>)}
        {detail.approvals.length === 0 ? <p className="muted">No approvals yet.</p> : null}
      </div></section>
    </div>

    <section className="card section"><h2 className="sectionTitle">Delivery</h2>
      <div className="grid two">
        <div><div className="muted">Current build</div><div className="mono">{detail.currentBuildHash ?? "—"}</div></div>
        <div>
          <div className="muted">Latest production deployment</div>
          <div>{latestProduction?.url || "—"}</div>
          {latestProduction ? (
            <Link className="button secondaryButton" href={`/clients/${clientId}/deployments/${latestProduction.id}`} style={{ marginTop: 10 }}>
              View deployment logs
            </Link>
          ) : null}
        </div>
      </div>
      {latestPreview ? <div className="previewRow"><div><div className="muted">Preview</div><a href={latestPreview.url} target="_blank" rel="noreferrer">{latestPreview.url}</a></div><span className="badge">{latestPreview.status}</span></div> : null}
    </section>

    {detail.state === "LIVE" ? (
      <section className="card section">
        <h2 className="sectionTitle">Custom domain</h2>
        <p className="muted">Attach the client's public DNS hostname to the live site.</p>
        <form className="domainForm" action={`/api/clients/${clientId}/action`} method="post">
          <input type="hidden" name="action" value="attach-domain" />
          <input type="hidden" name="client_id" value={clientId} />
          <div className="domainRow">
            <input
              name="fqdn"
              type="text"
              inputMode="url"
              autoComplete="off"
              placeholder="www.example.com"
              aria-label="Custom domain"
              maxLength={253}
              required
            />
            <button className="button" type="submit">Attach domain</button>
          </div>
        </form>
      </section>
    ) : null}

    {detail.state === "LIVE" && rollbackTargets.length > 0 ? (
      <section className="card section">
        <div className="detailHeader"><div><h2 className="sectionTitle">Rollback</h2><div className="muted">Restore a previously approved build for this client.</div></div></div>
        <div className="list">
          {rollbackTargets.map((version) => (
            <div className="row" key={version.id}>
              <div><strong>{version.buildHash.slice(0, 12)}…</strong><div className="muted">{version.designPresetId} · {version.templateVersion}</div></div>
              <ActionForm action="rollback" clientId={clientId} hidden={{ build_hash: version.buildHash }}>Rollback to this build</ActionForm>
            </div>
          ))}
        </div>
      </section>
    ) : null}
  </>;
}