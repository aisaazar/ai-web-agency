"use client";

import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import type { ContentModel } from "@ai-web-agency/contracts";

type ContactForm = ContentModel["contact"]["form"];

const EMAIL_PATTERN = /^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$/u;
const LEAD_API_URL = process.env.NEXT_PUBLIC_AGENCY_LEAD_API_URL?.replace(/\/$/u, "");
const SITE_ID = process.env.NEXT_PUBLIC_AGENCY_SITE_ID;

interface FieldValues {
  name: string;
  email: string;
  phone: string;
  message: string;
  consent: boolean;
}

const EMPTY_VALUES: FieldValues = { name: "", email: "", phone: "", message: "", consent: false };
const FIELD_IDS = { name: "lead-name", email: "lead-email", phone: "lead-phone", message: "lead-message", consent: "lead-consent", honeypot: "lead-website" } as const;
const INPUT_CLASS = "mt-1 w-full rounded-md border border-line bg-surface px-3 py-2 text-ink";

export function LeadForm({ form }: { form: ContactForm }) {
  const [values, setValues] = useState<FieldValues>(EMPTY_VALUES);
  const [errors, setErrors] = useState<string[]>([]);
  const [state, setState] = useState<"idle" | "submitting" | "success" | "failure">("idle");
  const [startedAt] = useState(() => new Date().toISOString());
  const [honeypot, setHoneypot] = useState("");
  const errorSummaryRef = useRef<HTMLDivElement>(null);

  const update =
    (field: keyof FieldValues) =>
    (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const target = event.target;
      const nextValue = target instanceof HTMLInputElement && target.type === "checkbox" ? target.checked : target.value;
      setValues((current) => ({ ...current, [field]: nextValue }));
      setState("idle");
    };

  function validate(): string[] {
    const nextErrors: string[] = [];
    if (values.name.trim().length === 0) nextErrors.push("name");
    if (values.email.trim().length === 0) nextErrors.push("email");
    else if (!EMAIL_PATTERN.test(values.email.trim())) nextErrors.push("email:format");
    if (values.message.trim().length === 0) nextErrors.push("message");
    if (!values.consent) nextErrors.push("consent");
    return nextErrors;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextErrors = validate();
    setErrors(nextErrors);
    if (nextErrors.length > 0) {
      setState("idle");
      errorSummaryRef.current?.focus();
      return;
    }
    if (!LEAD_API_URL || !SITE_ID) {
      setState("failure");
      return;
    }

    setState("submitting");
    try {
      const response = await fetch(`${LEAD_API_URL}/v1/leads`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          site_id: SITE_ID,
          name: values.name.trim(),
          email: values.email.trim(),
          phone: values.phone.trim() || null,
          message: values.message.trim(),
          consent: values.consent,
          website: honeypot,
          form_started_at: startedAt,
        }),
      });
      if (!response.ok) throw new Error(`lead request failed: ${response.status}`);
      setState("success");
      setErrors([]);
      setValues(EMPTY_VALUES);
      setHoneypot("");
    } catch {
      setState("failure");
    }
  }

  const hasError = (field: string) => errors.some((error) => error.startsWith(field));
  const messageFor = (field: string) => errors.includes(`${field}:format`) ? form.labels.error_email : form.labels.error_required;

  return (
    <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-5">
      <div ref={errorSummaryRef} tabIndex={-1} role={errors.length > 0 ? "alert" : undefined} className={errors.length > 0 ? "rounded-md border border-accent-600 bg-accent-100 p-4" : ""}>
        {errors.length > 0 ? (
          <div className="text-sm text-accent-700">
            <strong className="font-semibold">{form.labels.error_summary}</strong>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              {[...new Set(errors.map((error) => error.split(":")[0]))].map((field) => (
                <li key={field}><a className="underline" href={`#${FIELD_IDS[field as keyof typeof FIELD_IDS]}`}>{messageFor(field)}</a></li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <p className="text-sm text-ink-muted">{form.labels.required_hint} {form.labels.optional_hint}</p>

      <div><label htmlFor={FIELD_IDS.name} className="block text-sm font-medium text-ink">{form.labels.name} <span aria-hidden="true">*</span></label><input id={FIELD_IDS.name} name="name" type="text" required autoComplete="name" value={values.name} onChange={update("name")} aria-invalid={hasError("name")} aria-describedby={hasError("name") ? "lead-name-error" : undefined} className={INPUT_CLASS} />{hasError("name") ? <p id="lead-name-error" className="mt-1 text-sm text-accent-700">{form.labels.error_required}</p> : null}</div>

      <div><label htmlFor={FIELD_IDS.email} className="block text-sm font-medium text-ink">{form.labels.email} <span aria-hidden="true">*</span></label><input id={FIELD_IDS.email} name="email" type="email" required autoComplete="email" value={values.email} onChange={update("email")} aria-invalid={hasError("email")} aria-describedby={hasError("email") ? "lead-email-error" : undefined} className={INPUT_CLASS} />{hasError("email") ? <p id="lead-email-error" className="mt-1 text-sm text-accent-700">{messageFor("email")}</p> : null}</div>

      <div><label htmlFor={FIELD_IDS.phone} className="block text-sm font-medium text-ink">{form.labels.phone} <span className="text-ink-muted">({form.labels.phone_optional})</span></label><input id={FIELD_IDS.phone} name="phone" type="tel" autoComplete="tel" value={values.phone} onChange={update("phone")} className={INPUT_CLASS} /></div>

      <div><label htmlFor={FIELD_IDS.message} className="block text-sm font-medium text-ink">{form.labels.message} <span aria-hidden="true">*</span></label><textarea id={FIELD_IDS.message} name="message" rows={5} required value={values.message} onChange={update("message")} aria-invalid={hasError("message")} aria-describedby={hasError("message") ? "lead-message-error" : undefined} className={INPUT_CLASS} />{hasError("message") ? <p id="lead-message-error" className="mt-1 text-sm text-accent-700">{form.labels.error_required}</p> : null}</div>

      <div className="hidden" aria-hidden="true"><label htmlFor={FIELD_IDS.honeypot}>Website</label><input id={FIELD_IDS.honeypot} name="website" type="text" tabIndex={-1} autoComplete="off" value={honeypot} onChange={(event) => setHoneypot(event.target.value)} /></div>

      <div className="flex items-start gap-3"><input id={FIELD_IDS.consent} name="consent" type="checkbox" required checked={values.consent} onChange={update("consent")} aria-invalid={hasError("consent")} aria-describedby={hasError("consent") ? "lead-consent-error" : undefined} className="mt-1 h-4 w-4" /><label htmlFor={FIELD_IDS.consent} className="text-sm text-ink-muted">{form.consent_label}</label></div>
      {hasError("consent") ? <p id="lead-consent-error" className="text-sm text-accent-700">{form.labels.error_required}</p> : null}

      <button type="submit" disabled={state === "submitting"} className="inline-flex items-center justify-center rounded-md bg-brand-600 px-5 py-3 text-base font-semibold text-surface hover:bg-brand-700 disabled:cursor-wait disabled:opacity-70">{state === "submitting" ? form.submitting_label : form.submit_label}</button>
      <p role="status" aria-live="polite" className="text-sm text-ink-muted">
        {state === "success" ? form.success_message : state === "failure" ? form.failure_message : !LEAD_API_URL || !SITE_ID ? form.offline_notice : ""}
      </p>
    </form>
  );
}
