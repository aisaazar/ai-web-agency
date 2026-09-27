"""Customer-facing assistant over approved site content only."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.conversation_models import Conversation, ConversationMessage
from agency.db.models import Approval, Artifact, Client

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


def _approved_content(session: Session, *, client_id, org_id) -> dict:
    artifact = session.scalar(
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
    )
    if artifact is None:
        raise AgentError("no approved content is available")
    facts_artifact = session.get(Artifact, artifact.input_artifact_id) if artifact.input_artifact_id else None
    if facts_artifact is None or facts_artifact.org_id != org_id:
        raise AgentError("approved content is not bound to client facts")
    if facts_artifact.payload_json.get("client_id") != str(client_id):
        raise AgentError("approved content does not belong to client")
    return artifact.payload_json


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
