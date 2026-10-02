export const PROSPECT_STATUSES = [
  "new",
  "contacted",
  "qualified",
  "converted",
  "dismissed",
] as const;

export type ProspectStatus = typeof PROSPECT_STATUSES[number];

export const WEBSITE_STATUSES = [
  "missing",
  "poor",
  "unknown",
  "good",
] as const;

export type WebsiteStatus = typeof WEBSITE_STATUSES[number];
