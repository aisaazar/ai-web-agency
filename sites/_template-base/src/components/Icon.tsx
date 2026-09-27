import type { Icon as IconName } from "@ai-web-agency/contracts";

/**
 * Inline SVG icon set. The content model carries an allowlisted `icon` name (`IconName` literal), so
 * a generated artifact can never inject markup or request a remote icon font. Icons are decorative
 * (`aria-hidden`) and always accompanied by visible text — colour and shape are never the only
 * signal.
 */
const PATHS: Record<IconName, string> = {
  tooth: "M12 3c2 0 3 1 4.5 1S19 3.5 20 4.5c1.4 1.4 1 4.2.5 6-.4 1.5-.6 3.4-.8 5.3-.2 2-.4 4-1.6 4.9-1.2.9-2-.4-2.3-1.3-.3-.9-.6-2.6-1.6-2.6h-2.4c-1 0-1.3 1.7-1.6 2.6-.3.9-1.1 2.2-2.3 1.3-1.2-.9-1.4-2.9-1.6-4.9-.2-1.9-.4-3.8-.8-5.3-.5-1.8-.9-4.6.5-6C5.5 3.5 6.5 4 7.5 4S10 3 12 3Z",
  sparkle: "M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6L12 3Zm6 10l.8 2.2L21 16l-2.2.8L18 19l-.8-2.2L15 16l2.2-.8L18 13Z",
  shield: "M12 3l7 3v5c0 4.2-2.9 8.2-7 9.4C7.9 19.2 5 15.2 5 11V6l7-3Zm-1 6v2H9v2h2v2h2v-2h2v-2h-2V9h-2Z",
  clock: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm1 4v4.6l3.2 1.9-1 1.7L11 13V7h2Z",
  phone:
    "M6.6 3h3l1.5 4-2 1.5a12 12 0 0 0 5.4 5.4l1.5-2 4 1.5v3a2 2 0 0 1-2.2 2A16.5 16.5 0 0 1 4.6 5.2 2 2 0 0 1 6.6 3Z",
  "map-pin": "M12 3a7 7 0 0 0-7 7c0 5 7 11 7 11s7-6 7-11a7 7 0 0 0-7-7Zm0 9.5A2.5 2.5 0 1 1 12 7.5a2.5 2.5 0 0 1 0 5Z",
  users:
    "M8 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5H2Zm13.5-5c2.5.3 4.5 2.3 4.5 5h-4c0-1.9-.6-3.6-1.6-4.8.4-.1.7-.2 1.1-.2Z",
  heart:
    "M12 20s-7-4.3-7-9a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 4.7-7 9-7 9Z",
  child:
    "M12 4a2 2 0 1 1 0 4 2 2 0 0 1 0-4ZM9 9h6l1 5h-2v6h-1.5v-4h-1v4H10v-6H8l1-5Z",
  calendar:
    "M7 2v2H5.5A1.5 1.5 0 0 0 4 5.5v13A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5v-13A1.5 1.5 0 0 0 18.5 4H17V2h-2v2H9V2H7Zm-1 7h12v9H6V9Z",
};

export function Icon({ name, className = "h-6 w-6" }: { name: IconName; className?: string }) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
