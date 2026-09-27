"use client";

import { FormEvent, useState } from "react";

import { UI } from "@/lib/ui-strings";

type AgentMessage = {
  role: "user" | "assistant";
  message: string;
  escalated?: boolean;
};

const API_URL = process.env.NEXT_PUBLIC_AGENCY_AGENT_API_URL?.replace(/\/$/u, "");
const CLIENT_ID = process.env.NEXT_PUBLIC_AGENCY_CLIENT_ID;

export function AgentWidget() {
  const [consent, setConsent] = useState(false);
  const [started, setStarted] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!API_URL || !CLIENT_ID) return null;

  async function startConversation() {
    if (!consent || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${API_URL}/v1/agent/clients/${CLIENT_ID}/conversations`,
        {
          method: "POST",
          credentials: "include",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ consent: true }),
        },
      );
      if (!response.ok) throw new Error(`agent start failed: ${response.status}`);
      const data = (await response.json()) as { conversation_id: string };
      setConversationId(data.conversation_id);
      setStarted(true);
    } catch {
      setError(UI.agentUnavailable);
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !conversationId || busy) return;

    setBusy(true);
    setError("");
    setMessages((current) => [...current, { role: "user", message: text }]);
    setDraft("");
    try {
      const response = await fetch(
        `${API_URL}/v1/agent/conversations/${conversationId}/messages`,
        {
          method: "POST",
          credentials: "include",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ message: text }),
        },
      );
      if (!response.ok) throw new Error(`agent message failed: ${response.status}`);
      const data = (await response.json()) as {
        message: string;
        escalated: boolean;
      };
      setMessages((current) => [
        ...current,
        { role: "assistant", message: data.message, escalated: data.escalated },
      ]);
    } catch {
      setMessages((current) => current.slice(0, -1));
      setDraft(text);
      setError(UI.agentUnavailable);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="agent-heading" className="py-12 sm:py-16">
      <div className="mx-auto w-full max-w-5xl px-4 sm:px-6 lg:px-8">
        <div className="rounded-xl border border-line bg-surface-muted p-5 shadow-sm sm:p-7">
          <div className="mb-6">
            <h2 id="agent-heading" className="text-2xl font-semibold text-ink sm:text-3xl">
              {UI.agentHeading}
            </h2>
            <p className="mt-2 text-ink-muted">{UI.agentIntro}</p>
          </div>

          {!started ? (
            <div className="space-y-5">
              <label className="flex items-start gap-3 text-sm text-ink-muted">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                  className="mt-1 h-4 w-4"
                />
                <span>{UI.agentConsent}</span>
              </label>
              <button
                type="button"
                onClick={startConversation}
                disabled={!consent || busy}
                className="inline-flex items-center justify-center rounded-md bg-brand-600 px-5 py-3 font-semibold text-surface hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {busy ? UI.agentStarting : UI.agentStart}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div
                aria-live="polite"
                className="max-h-80 space-y-3 overflow-y-auto rounded-lg border border-line bg-surface p-4"
              >
                {messages.length === 0 ? (
                  <p className="text-sm text-ink-muted">{UI.agentIntro}</p>
                ) : (
                  messages.map((item, index) => (
                    <div
                      key={`${item.role}-${index}`}
                      className={`rounded-lg p-3 text-sm ${item.role === "user" ? "ml-8 bg-brand-50 text-ink" : "mr-8 bg-surface-muted text-ink"}`}
                    >
                      <p>{item.message}</p>
                      {item.escalated ? (
                        <p className="mt-2 font-medium text-accent-700">{UI.agentEscalated}</p>
                      ) : null}
                    </div>
                  ))
                )}
              </div>

              {error ? <p role="alert" className="text-sm text-accent-700">{error}</p> : null}

              <form onSubmit={sendMessage} className="flex flex-col gap-3 sm:flex-row">
                <label htmlFor="agent-message" className="sr-only">{UI.agentPlaceholder}</label>
                <input
                  id="agent-message"
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  placeholder={UI.agentPlaceholder}
                  maxLength={5000}
                  className="min-w-0 flex-1 rounded-md border border-line bg-surface px-3 py-3 text-ink"
                />
                <button
                  type="submit"
                  disabled={busy || !draft.trim()}
                  className="inline-flex items-center justify-center rounded-md bg-brand-600 px-5 py-3 font-semibold text-surface hover:bg-brand-700 disabled:cursor-wait disabled:opacity-60"
                >
                  {busy ? UI.agentSending : UI.agentSend}
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
