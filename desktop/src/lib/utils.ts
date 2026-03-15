export function clamp(n: number, a: number, b: number): number {
  return Math.max(a, Math.min(b, n));
}

export function fmtPct(v: number): string {
  return `${Math.round(clamp(v, 0, 1) * 100)}%`;
}

export function basename(p: string): string {
  return p.match(/[^/\\]+$/)?.[0] || p;
}

export function truncate(s: string, max = 900): string {
  return s.length <= max ? s : s.slice(0, max - 1) + "…";
}

export function formatTime(s: number): string {
  if (!isFinite(s) || s < 0) return "0:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export async function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export async function tryCopy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}