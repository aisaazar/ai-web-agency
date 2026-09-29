"""Public customer-assistant endpoints scoped to one client."""

from uuid import UUID
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from agency.api.agent_schemas import (
    AgentMessageIn,
    AgentMessageOut,
    ConversationCreateIn,
    ConversationCreateOut,
    ConversationMessageOut,
)
from agency.api.dependencies import get_db
from agency.db.conversation_models import Conversation, ConversationMessage
from agency.services.agent_service import AgentError, CONSENT_NOTICE, reply_to_conversation, start_conversation

VISITOR_COOKIE = "agency_agent_visitor"
VISITOR_HEADER = "X-Agent-Visitor-Token"


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/agent", tags=["customer-agent"])
    db = get_db(session_factory)

    def set_visitor_cookie(response: Response, visitor_ref: str) -> None:
        secure = os.getenv("AGENCY_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
        samesite = os.getenv("AGENCY_AGENT_COOKIE_SAMESITE", "lax").strip().lower()
        if samesite not in {"lax", "strict", "none"}:
            samesite = "lax"
        response.set_cookie(
            VISITOR_COOKIE,
            visitor_ref,
            max_age=24 * 60 * 60,
            httponly=True,
            secure=secure,
            samesite=samesite,
            path="/",
        )

    @router.post("/clients/{client_id}/conversations", response_model=ConversationCreateOut, status_code=201)
    def create_conversation(
        client_id: UUID,
        payload: ConversationCreateIn,
        response: Response,
        session: Session = Depends(db),
    ):
        try:
            conversation, notice = start_conversation(
                session,
                org_id=_resolve_org_id(session, client_id),
                client_id=client_id,
                consent=payload.consent,
            )
        except AgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        set_visitor_cookie(response, conversation.visitor_ref)
        return ConversationCreateOut(
            conversation_id=conversation.id,
            visitor_token=conversation.visitor_ref,
            consent_notice=notice,
        )

    @router.post("/conversations/{conversation_id}/messages", response_model=AgentMessageOut)
    def message(
        conversation_id: UUID,
        payload: AgentMessageIn,
        request: Request,
        session: Session = Depends(db),
    ):
        visitor_ref = request.headers.get(VISITOR_HEADER) or request.cookies.get(VISITOR_COOKIE)
        if not visitor_ref:
            raise HTTPException(status_code=401, detail="agent visitor session required")
        try:
            conversation, answer, escalated, contact = reply_to_conversation(
                session,
                conversation_id=conversation_id,
                visitor_ref=visitor_ref,
                message=payload.message,
            )
        except AgentError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return AgentMessageOut(
            conversation_id=conversation.id,
            role="assistant",
            message=answer,
            escalated=escalated,
            contact_phone=contact.get("phone"),
            contact_email=contact.get("email"),
        )

    @router.get("/conversations/{conversation_id}/messages", response_model=list[ConversationMessageOut])
    def messages(
        conversation_id: UUID,
        request: Request,
        session: Session = Depends(db),
    ):
        visitor_ref = request.headers.get(VISITOR_HEADER) or request.cookies.get(VISITOR_COOKIE)
        conversation = session.get(Conversation, conversation_id)
        if conversation is None or conversation.visitor_ref != visitor_ref:
            raise HTTPException(status_code=404, detail="conversation not found")
        rows = session.scalars(
            select(ConversationMessage)
            .where(
                ConversationMessage.conversation_id == conversation.id,
                ConversationMessage.org_id == conversation.org_id,
            )
            .order_by(ConversationMessage.created_at.asc())
        )
        return [
            ConversationMessageOut(
                role=row.role,
                message=row.content_redacted,
                escalated=row.escalated,
                created_at=row.created_at,
            )
            for row in rows
        ]

    return router


def _resolve_org_id(session: Session, client_id: UUID):
    from agency.db.models import Client

    client = session.scalar(select(Client).where(Client.id == client_id))
    if client is None:
        raise AgentError("client not found")
    return client.org_id
