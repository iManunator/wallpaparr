export function providerToast(result: { ok?: boolean; message?: string; error?: string } | null | undefined): {
  kind: "ok" | "error";
  text: string;
} {
  const text = result?.message || result?.error || (result?.ok ? "Connected" : "Connection failed");
  return { kind: result?.ok ? "ok" : "error", text };
}

export function generateToast(result: { message?: string; count?: number; warnings?: string[] } | null | undefined): {
  kind: "ok" | "error" | "info";
  text: string;
} {
  const text = result?.message || `Created ${result?.count ?? 0} stills.`;
  if ((result?.count ?? 0) === 0 && (result?.warnings?.length ?? 0) > 0) return { kind: "info", text };
  if ((result?.count ?? 0) === 0) return { kind: "info", text };
  return { kind: "ok", text };
}

export function motionToast(result: { message?: string; count?: number; generated?: string[]; style?: string } | null | undefined): {
  kind: "ok" | "info";
  text: string;
} {
  const n = result?.count ?? result?.generated?.length ?? 0;
  const text = result?.message || (n ? `Baked motion VIDEO for ${n} title${n === 1 ? "" : "s"}.` : "No VIDEO clips baked.");
  return { kind: n ? "ok" : "info", text };
}

export function errorToast(err: unknown, fallback: string): { kind: "error"; text: string } {
  const raw = err instanceof Error ? err.message : String(err || fallback);
  let text = raw;
  try {
    const parsed = JSON.parse(raw) as { detail?: string };
    if (parsed?.detail) text = parsed.detail;
  } catch {
    /* keep raw */
  }
  return { kind: "error", text: text || fallback };
}
