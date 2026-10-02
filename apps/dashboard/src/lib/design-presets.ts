/**
 * The closed set of design presets the shared static template can build
 * (`sites/_presets/<id>.json`).
 *
 * Mirrors `agency.domain.design_presets.SUPPORTED_DESIGN_PRESET_IDS`. Dashboard intake validation
 * and the client detail preset resolution read this list, so the dashboard can never persist or act
 * on a preset the pipeline would reject later.
 */
export const DESIGN_PRESETS = ["health", "corporate", "warm"] as const;

export type DesignPresetId = (typeof DESIGN_PRESETS)[number];

/**
 * Operator-facing labels. Keyed by the same ids as `DESIGN_PRESETS` so a preset can never be
 * offered in the UI without also being a value the API accepts.
 */
export const DESIGN_PRESET_LABELS: Record<DesignPresetId, string> = {
  health: "Health / Praxis",
  corporate: "Corporate / Professional",
  warm: "Warm / Human",
};

export function isDesignPresetId(value: string): value is DesignPresetId {
  return (DESIGN_PRESETS as readonly string[]).includes(value);
}
