// Formatting helpers shared across pages. All data is pre-shaped by the
// export script; these only handle presentation.

const MONTHS_FR = [
  "JANV", "FÉVR", "MARS", "AVR", "MAI", "JUIN",
  "JUIL", "AOÛT", "SEPT", "OCT", "NOV", "DÉC",
];

/** "12 JUIL · 21:00" — kickoff in a compact mono-friendly form (UTC). */
export function kickoff(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const day = d.getUTCDate();
  const mon = MONTHS_FR[d.getUTCMonth()];
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${day} ${mon} · ${hh}:${mm}`;
}

/** "2026-07-12 13:22 UTC" — for the status line. */
export function stamp(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())} UTC`;
}

/** Full-time score, or a dash for fixtures not yet played. */
export function score(h: number | null, a: number | null): string {
  if (h == null || a == null) return "–";
  return `${h}–${a}`;
}

/** Penalty shoot-out suffix, e.g. "(4–2 t.a.b.)". */
export function penalties(h: number | null, a: number | null): string | null {
  if (h == null || a == null) return null;
  return `${h}–${a} t.a.b.`;
}

export function groupLabel(code: string): string {
  return `Groupe ${code}`;
}

const STAGE_FR: Record<string, string> = {
  GROUP_STAGE: "Phase de groupes",
  LAST_32: "16es de finale",
  LAST_16: "8es de finale",
  QUARTER_FINALS: "Quarts de finale",
  SEMI_FINALS: "Demi-finales",
  THIRD_PLACE: "Match pour la 3e place",
  FINAL: "Finale",
};

export function stageLabel(stage: string): string {
  return STAGE_FR[stage] ?? stage;
}

