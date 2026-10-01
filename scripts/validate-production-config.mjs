#!/usr/bin/env node
/**
 * Production runtime preflight.
 * Validates required server-side configuration without printing secret values.
 */
const failures = [];

const required = (name) => {
  const value = process.env[name]?.trim() ?? "";
  if (!value) failures.push(`${name} is required`);
  return value;
};

const environment = required("AGENCY_ENV");
if (environment && environment.toLowerCase() !== "production") {
  failures.push("AGENCY_ENV must be production");
}

const databaseUrl = required("AGENCY_DATABASE_URL");
if (databaseUrl && /^sqlite:\/\/\/?agency\.db$/i.test(databaseUrl)) {
  failures.push("AGENCY_DATABASE_URL must not use the default local agency.db path");
}

const origins = required("AGENCY_ALLOWED_ORIGINS");
if (origins) {
  for (const origin of origins.split(",").map((item) => item.trim()).filter(Boolean)) {
    try {
      const url = new URL(origin);
      if (url.protocol !== "https:") failures.push("AGENCY_ALLOWED_ORIGINS must contain HTTPS origins only");
      if (url.username || url.password) failures.push("AGENCY_ALLOWED_ORIGINS must not contain credentials");
      if (url.pathname !== "/" || url.search || url.hash) failures.push("AGENCY_ALLOWED_ORIGINS entries must be origins, not paths or queries");
    } catch {
      failures.push("AGENCY_ALLOWED_ORIGINS contains an invalid URL");
    }
  }
  if (origins.split(",").some((item) => item.trim() === "*")) {
    failures.push("AGENCY_ALLOWED_ORIGINS must not contain *");
  }
}

const secureCookie = (process.env.AGENCY_COOKIE_SECURE ?? "").trim().toLowerCase();
if (!["1", "true", "yes"].includes(secureCookie)) {
  failures.push("AGENCY_COOKIE_SECURE=true is required");
}

required("AGENCY_TURNSTILE_SECRET");

const legacyUnauth = (process.env.AGENCY_ALLOW_LEGACY_UNAUTH ?? "").trim().toLowerCase();
if (["1", "true", "yes"].includes(legacyUnauth)) {
  failures.push("AGENCY_ALLOW_LEGACY_UNAUTH is forbidden in production");
}

const provider = required("AGENCY_DEPLOY_PROVIDER").toLowerCase();
if (provider !== "vercel") {
  failures.push("Production deployment requires AGENCY_DEPLOY_PROVIDER=vercel");
}
if (provider === "vercel") {
  required("VERCEL_PROJECT_ID");
  required("VERCEL_TOKEN");
}

const researchProvider = required("AGENCY_RESEARCH_PROVIDER").toLowerCase();
if (researchProvider === "tavily") required("TAVILY_API_KEY");
if (researchProvider !== "tavily") {
  failures.push("Production research requires AGENCY_RESEARCH_PROVIDER=tavily");
}

const llmProvider = required("AGENCY_LLM_PROVIDER").toLowerCase();
if (llmProvider !== "local") {
  failures.push("Production content generation requires AGENCY_LLM_PROVIDER=local");
} else {
  const llmBaseUrl = required("AGENCY_LOCAL_LLM_BASE_URL");
  const llmModel = required("AGENCY_LOCAL_LLM_MODEL");
  if (llmBaseUrl) {
    try {
      const url = new URL(llmBaseUrl);
      if (!["http:", "https:"].includes(url.protocol)) failures.push("AGENCY_LOCAL_LLM_BASE_URL must use HTTP or HTTPS");
      if (url.username || url.password) failures.push("AGENCY_LOCAL_LLM_BASE_URL must not contain credentials");
    } catch {
      failures.push("AGENCY_LOCAL_LLM_BASE_URL is not a valid URL");
    }
  }
  if (llmModel && /qwen3:0\.6b$/u.test(llmModel)) {
    failures.push("AGENCY_LOCAL_LLM_MODEL must use the bounded-context Agency model (for example agency-qwen3-8k)");
  }
}

const notifyProvider = required("AGENCY_NOTIFY_PROVIDER").toLowerCase();
if (notifyProvider !== "smtp") {
  failures.push("Production notifications require AGENCY_NOTIFY_PROVIDER=smtp");
} else {
  required("AGENCY_SMTP_HOST");
  const smtpFrom = required("AGENCY_SMTP_FROM");
  const notificationTo = required("AGENCY_LEAD_NOTIFICATION_TO");
  const smtpPortRaw = required("AGENCY_SMTP_PORT");
  const smtpPort = Number.parseInt(smtpPortRaw, 10);
  if (smtpPortRaw && (!Number.isInteger(smtpPort) || smtpPort < 1 || smtpPort > 65535)) {
    failures.push("AGENCY_SMTP_PORT must be an integer from 1 to 65535");
  }
  if (smtpFrom && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/u.test(smtpFrom)) {
    failures.push("AGENCY_SMTP_FROM must be a valid email address");
  }
  if (notificationTo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/u.test(notificationTo)) {
    failures.push("AGENCY_LEAD_NOTIFICATION_TO must be a valid email address");
  }
  const smtpUsername = (process.env.AGENCY_SMTP_USERNAME || "").trim();
  const smtpPassword = (process.env.AGENCY_SMTP_PASSWORD || "").trim();
  if (Boolean(smtpUsername) !== Boolean(smtpPassword)) {
    failures.push("AGENCY_SMTP_USERNAME and AGENCY_SMTP_PASSWORD must be set together");
  }
}

if (failures.length) {
  console.error("Production runtime preflight failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Production runtime preflight passed: required server configuration is present and structurally safe.");
