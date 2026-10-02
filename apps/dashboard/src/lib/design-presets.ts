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

export function isDesignPresetId(value: string): value is DesignPresetId {
  return (DESIGN_PRESETS as readonly string[]).includes(value);
}
