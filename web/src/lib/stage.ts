/** Fit a 16:9 wallpaper stage inside a parent (object-fit: contain). */

export const STAGE_ASPECT = 16 / 9;

export type StageSize = { width: number; height: number };

/**
 * Scale a 16:9 rectangle so it never exceeds parent width or remaining
 * viewport height. Centered letterboxing is the caller's job (flex + margin).
 */
export function fitStageContain(
  parentWidth: number,
  viewportHeight: number,
  chromePx = 224,
): StageSize {
  const safeParent = Math.max(0, parentWidth);
  const maxHeight = Math.max(120, Math.min(viewportHeight * 0.68, viewportHeight - chromePx));
  const width = Math.min(safeParent, maxHeight * STAGE_ASPECT);
  const height = width / STAGE_ASPECT;
  return { width, height };
}

export function stageOverflowsParent(
  stage: StageSize,
  parent: StageSize,
  epsilon = 0.51,
): boolean {
  return stage.width > parent.width + epsilon || stage.height > parent.height + epsilon;
}

export function stageAspectRatio(stage: StageSize): number {
  if (stage.height <= 0) return STAGE_ASPECT;
  return stage.width / stage.height;
}
