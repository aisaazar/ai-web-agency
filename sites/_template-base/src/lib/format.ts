/**
 * Presentation-only formatting helpers. Every string shown to a human is pure formatting of typed
 * content — no copy is authored here, and no LLM output reaches the DOM untyped.
 */
import type { Address, Business, ContactDetails, OpeningHours1 } from "@ai-web-agency/contracts";

type Weekday = "Mo" | "Tu" | "We" | "Th" | "Fr" | "Sa" | "Su";

const WEEKDAY_LABELS: Record<Weekday, string> = {
  Mo: "Montag",
  Tu: "Dienstag",
  We: "Mittwoch",
  Th: "Donnerstag",
  Fr: "Freitag",
  Sa: "Samstag",
  Su: "Sonntag",
};

/** Weekdays in display order, so grouped opening hours never sort differently per render. */
const WEEKDAY_ORDER: Weekday[] = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

export function formatWeekdays(days: Weekday[]): string {
  return [...days]
    .sort((a, b) => WEEKDAY_ORDER.indexOf(a) - WEEKDAY_ORDER.indexOf(b))
    .map((day) => WEEKDAY_LABELS[day])
    .join(", ");
}

export function formatSlots(hours: OpeningHours1): string {
  return hours.slots.map((slot) => `${slot.opens}-${slot.closes} Uhr`).join(" und ");
}

/** One line of address, used in text and inside `<address>`. */
export function formatAddress(address: Address): string {
  const region = address.region ? `, ${address.region}` : "";
  return `${address.street}, ${address.postal_code} ${address.city}${region}, ${address.country}`;
}

/** `tel:` hrefs must not contain spaces or dashes; the visible label keeps them. */
export function phoneHref(phone: string): string {
  return `tel:${phone.replace(/[^+\d]/gu, "")}`;
}

export function mailtoHref(email: string): string {
  return `mailto:${email}`;
}

export function languagesLabel(business: Business): string {
  return business.spoken_languages.map((language) => language.toUpperCase()).join(", ");
}

export function insuranceLabel(business: Business): string {
  return business.insurance.map((kind) => kind.charAt(0).toUpperCase() + kind.slice(1)).join(", ");
}

/** Initials are the accessible stand-in for a missing, unapproved team photo. */
export function initials(name: string): string {
  return name
    .replace(/\b(?:Dr|med|dent|Prof)\b\.?/giu, "")
    .trim()
    .split(/\s+/u)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

/** German date rendering from an ISO date, deterministic (no locale-dependent formatting). */
export function formatIsoDate(iso: string): string {
  const parts = iso.split("-");
  const [year, month, day] = parts;
  return day && month && year ? `${day}.${month}.${year}` : iso;
}

export function formatEmergencyContact(contact: ContactDetails): string | null {
  if (!contact.emergency_phone) {
    return null;
  }
  return contact.emergency_phone;
}
