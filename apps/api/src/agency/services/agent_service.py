"""Customer-facing assistant over approved site content only."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.conversation_models import Conversation, ConversationMessage
from agency.db.models import Approval, Artifact, Client, Site, SiteVersion

CONSENT_NOTICE = (
    "Dieser Assistent beantwortet Fragen ausschließlich anhand freigegebener Website-Inhalte. "
    "Er ersetzt keine individuelle medizinische Beratung. Bitte geben Sie keine sensiblen Gesundheitsdaten ein."
)

_SAFE_TOKENS = {
    "die", "der", "das", "und", "oder", "ist", "sind", "wie", "was", "wo", "wann",
    "ich", "sie", "für", "mit", "von", "zum", "zur", "ein", "eine", "den", "dem", "auf",
}

_OUT_OF_SCOPE = (
    re.compile(r"\bdiagnos\w*\b|\bmedikament\w*\b|\bdosier\w*\b", re.I),
    re.compile(r"\b(?:heilen|heilung|garantiert|garantie)\b", re.I),
    re.compile(r"\bwas soll ich tun\b.*\b(?:schmerz|blutung|fieber)\b", re.I),
)
_PII = (
    (re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b"), "[E-MAIL REDACTED]"),
    (re.compile(r"(?<!\d)(?:\+?\d[\d ()/.\-]{7,}\d)(?!\d)"), "[PHONE REDACTED]"),
)

class AgentError(ValueError):
    pass


def _redact(text: str) -> str:
    value = text[:5000]
    for pattern, replacement in _PII:
        value = pattern.sub(replacement, value)
    return value


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[\wäöüß-]{3,}", text.lower())
        if token not in _SAFE_TOKENS
    }


def _bound_facts(session: Session, *, artifact: Artifact, org_id):
    """The client's active business facts a content artifact derives from, if that binding is still valid.

    docs/DOMAIN-MODEL.md: content copy may only derive from `client_facts` where `status = approved`.
    """
    if not artifact.input_artifact_id:
        return None
    facts = session.get(Artifact, artifact.input_artifact_id)
    if facts is None or facts.org_id != org_id:
        return None
    if facts.artifact_type != "business_facts" or not facts.is_active:
        return None
    return facts


def _shipped_by_another_client(
    session: Session, *, content_artifact_id, org_id, client_id
) -> bool:
    """True when another client's site already shipped this exact content revision."""
    return (
        session.scalar(
            select(SiteVersion.id)
            .join(Site, Site.id == SiteVersion.site_id)
            .where(
                SiteVersion.org_id == org_id,
                SiteVersion.content_artifact_id == content_artifact_id,
                Site.org_id == org_id,
                Site.client_id != client_id,
            )
            .limit(1)
        )
        is not None
    )


def _approved_content(session: Session, *, client_id, org_id) -> dict:
    """Approved copy that belongs to exactly this client.

    The newest org-wide approval is *not* the answer: candidates are scanned newest-first and only one
    bound to this client's active business facts is served, so a second client in the same org can never
    mask or inherit the assistant of another.
    """
    candidates = session.scalars(
        select(Artifact)
        .join(Approval, Approval.artifact_id == Artifact.id)
        .where(
            Artifact.org_id == org_id,
            Artifact.artifact_type == "content_model",
            Artifact.is_active.is_(True),
            Approval.org_id == org_id,
            Approval.gate == "CONTENT",
            Approval.decision == "approved",
        )
        .order_by(Approval.created_at.desc(), Artifact.created_at.desc())
    ).all()
    if not candidates:
        raise AgentError("no approved content is available")

    for artifact in candidates:
        if _shipped_by_another_client(
            session,
            content_artifact_id=artifact.id,
            org_id=org_id,
            client_id=client_id,
        ):
            continue
        facts = _bound_facts(session, artifact=artifact, org_id=org_id)
        if facts is None or facts.payload_json.get("client_id") != str(client_id):
            continue
        return artifact.payload_json
    raise AgentError("approved content is not bound to client facts")


def _contact(content: dict) -> dict[str, str | None]:
    contact = (content.get("business") or {}).get("contact") or {}
    return {"phone": contact.get("phone"), "email": contact.get("email")}
def _faq_candidates(content: dict, question: str) -> list[tuple[int, str]]:
    query_tokens = _tokens(question)
    items = ((content.get("faq") or {}).get("items") or [])
    candidates: list[tuple[int, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question") or "")
        answer = item.get("answer") or []
        answer_text = " ".join(str(v) for v in answer if isinstance(v, str))
        score = len(query_tokens & _tokens(q))
        if score:
            candidates.append((score, answer_text))
    return sorted(candidates, reverse=True)


def _content_candidates(content: dict, question: str) -> list[tuple[int, str]]:
    query_tokens = _tokens(question)
    candidates: list[tuple[int, str]] = []

    def walk(value: object, path: str = "") -> None:
        if isinstance(value, str) and len(value.strip()) >= 20:
            score = len(query_tokens & _tokens(value))
            if score:
                candidates.append((score, value.strip()))
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}.{index}")

    walk(content)
    return sorted(candidates, reverse=True)


def _answer(content: dict, question: str) -> tuple[str, bool]:
    if any(pattern.search(question) for pattern in _OUT_OF_SCOPE):
        contact = _contact(content)
        return (
            "Dabei kann ich keine individuelle medizinische Empfehlung oder Diagnose geben. "
            "Für eine persönliche Einschätzung wenden Sie sich bitte direkt an die Praxis. "
            f"Telefon: {contact.get('phone') or 'nicht angegeben'}; "
            f"E-Mail: {contact.get('email') or 'nicht angegeben'}.",
            True,
        )

    faq = _faq_candidates(content, question)
    candidates = faq or _content_candidates(content, question)
    if not candidates:
        contact = _contact(content)
        return (
            "Dazu finde ich in den freigegebenen Website-Inhalten keine verlässliche Antwort. "
            "Bitte kontaktieren Sie die Praxis direkt. "
            f"Telefon: {contact.get('phone') or 'nicht angegeben'}; "
            f"E-Mail: {contact.get('email') or 'nicht angegeben'}.",
            True,
        )
    return f"Laut den freigegebenen Website-Inhalten: {candidates[0][1]}", False


def start_conversation(session: Session, *, org_id, client_id, consent: bool) -> tuple[Conversation, str]:
    if not consent:
        raise AgentError(CONSENT_NOTICE)
    client = session.scalar(select(Client).where(Client.id == client_id, Client.org_id == org_id))
    if client is None:
        raise AgentError("client not found")
    conversation = Conversation(
        org_id=org_id,
        client_id=client_id,
        visitor_ref=secrets.token_urlsafe(24),
        consent_at=datetime.now(timezone.utc),
    )
    session.add(conversation)
    session.flush()
    return conversation, CONSENT_NOTICE
def reply_to_conversation(
    session: Session,
    *,
    conversation_id,
    visitor_ref: str,
    message: str,
) -> tuple[Conversation, str, bool, dict[str, str | None]]:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None or conversation.visitor_ref != visitor_ref:
        raise AgentError("conversation not found")
    text = message.strip()
    if not text or len(text) > 5000:
        raise AgentError("message must contain 1 to 5000 characters")

    content = _approved_content(
        session,
        client_id=conversation.client_id,
        org_id=conversation.org_id,
    )
    user_text = _redact(text)
    session.add(ConversationMessage(
        org_id=conversation.org_id,
        conversation_id=conversation.id,
        role="user",
        content_redacted=user_text,
    ))
    answer, escalated = _answer(content, text)
    session.add(ConversationMessage(
        org_id=conversation.org_id,
        conversation_id=conversation.id,
        role="assistant",
        content_redacted=_redact(answer),
        escalated=escalated,
    ))
    conversation.escalated = conversation.escalated or escalated
    session.flush()
    return conversation, answer, escalated, _contact(content)
