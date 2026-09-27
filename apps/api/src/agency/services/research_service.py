"""Research use case; provider access stays behind the research seam."""

from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact, Client
from agency.db.research_models import ResearchRun, ResearchSource
from agency.db.workflow_models import PipelineRun
from agency.providers.registry import get_research_provider
from agency.repositories import ArtifactRepository, PipelineRepository
from agency.services.pipeline_service import transition


def run_research(session: Session, *, org_id, client_id, provider_name: str = "mock") -> Artifact:
    client = session.scalar(select(Client).where(Client.id == client_id, Client.org_id == org_id))
    if client is None:
        raise ValueError("client not found")
    pipeline = PipelineRepository(session, org_id).latest_for_client(client.id)
    if pipeline is None or pipeline.state != "FACTS_APPROVED":
        raise ValueError("client is not ready for research")
    pipeline.state = transition(pipeline.state, "RESEARCHING").to_state

    provider = get_research_provider(provider_name)
    query = f"{client.name} {client.category} {client.jurisdiction}"
    run = ResearchRun(org_id=org_id, client_id=client.id, provider=provider.name, query_plan_json={"queries": [query]})
    session.add(run)
    session.flush()
    sources = provider.search(query, max_results=3)
    excerpts = []
    for source in sources:
        page = provider.fetch(source.url)
        fetched_at = datetime.now(timezone.utc)
        digest = sha256(page.text.encode("utf-8")).hexdigest()
        session.add(ResearchSource(
            org_id=org_id, research_run_id=run.id, url=page.url, title=page.title,
            fetched_at=fetched_at, content_hash=digest, excerpt=source.excerpt,
        ))
        excerpts.append({"url": page.url, "title": page.title, "excerpt": source.excerpt, "content_hash": digest})

    run.status = "complete"
    artifact = Artifact(
        org_id=org_id, artifact_type="research_report", schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "provider": provider.name, "query": query, "sources": excerpts},
        revision=1, is_active=True,
    )
    ArtifactRepository(session, org_id).add(artifact)
    pipeline.state = transition(pipeline.state, "RESEARCH_COMPLETE").to_state
    return artifact
