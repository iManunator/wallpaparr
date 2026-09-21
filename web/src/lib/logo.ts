export type TitleDisplay = "auto" | "logo" | "text";

export const LOGO_PADDING = 25;
export const LOGO_MAX_WIDTH = 1200;
export const LOGO_MAX_HEIGHT = 450;
export const PROJECTIVY_SAFE = { left: 72, top: 96, right: 72, bottom: 220 };

export function normalizeTitleDisplay(value: unknown): TitleDisplay {
  return value === "logo" || value === "text" ? value : "auto";
}

export function prefersLogo(mode: unknown): boolean {
  return normalizeTitleDisplay(mode) !== "text";
}

export function smartResizeLogo(
  srcW: number,
  srcH: number,
  maxW = LOGO_MAX_WIDTH,
  maxH = LOGO_MAX_HEIGHT,
): { width: number; height: number } {
  if (srcW <= 0 || srcH <= 0) return { width: 1, height: 1 };
  const ratio = srcW / srcH;
  let effectiveMaxH = maxH;
  if (ratio < 0.8) effectiveMaxH = maxH * 0.6;
  else if (ratio < 1.2) effectiveMaxH = maxH * 0.75;
  const scale = Math.min(maxW / srcW, effectiveMaxH / srcH);
  return { width: Math.max(1, Math.round(srcW * scale)), height: Math.max(1, Math.round(srcH * scale)) };
}

export function clampLogoRect(
  x: number,
  y: number,
  width: number,
  height: number,
  canvasW: number,
  canvasH: number,
): { x: number; y: number; width: number; height: number } {
  const maxX = Math.max(PROJECTIVY_SAFE.left, canvasW - PROJECTIVY_SAFE.right - width);
  const maxY = Math.max(PROJECTIVY_SAFE.top, canvasH - PROJECTIVY_SAFE.bottom - height);
  const nextX = Math.min(Math.max(x, PROJECTIVY_SAFE.left), maxX);
  const nextY = Math.min(Math.max(y, PROJECTIVY_SAFE.top), maxY);
  return { x: nextX, y: nextY, width, height };
}

export function tagShift(logoY: number, logoH: number, firstMetaY: number, padding = LOGO_PADDING): number {
  const desired = logoY + logoH + padding;
  return Math.max(0, Math.round(desired - firstMetaY));
}
