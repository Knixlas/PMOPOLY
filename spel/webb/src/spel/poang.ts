// Slutpoängen (regelboken kapitel 10) – samma formler som motorn:
//   PU  = ABT-budget ÷ (Q-krav + H-krav + T-påverkan)          motor/pu.py (resultat)
//   TG  = 100 × TB ÷ ABT-budget                                  motor/skede2.py (resultat)
//   Mu  = tabell efter antal avvikelser (10.2)                   motor/skede2.py MU
//   F   = (eget kapital + halva kassan − 100 × moderbolagslån) ÷ 30   motor/motor.py (f_poang, f_delare)
//   Slutpoäng = (PU + TG + F) × Mu
export const MU = [100, 80, 65, 53, 44, 37, 31, 27, 24, 21, 20];
export const F_DELARE = 30;
export const T_KRAV = 12;

export interface Siffror {
  abt: number; qKrav: number; hKrav: number; tPaverkan: number;      // Skede 1
  tb: number; q: number; h: number; t: number;                      // Skede 2 (utfallen)
  egetKapital: number; kassa: number; lan: number;                  // Förvaltningen
}

export const mu = (n: number) => (n <= 10 ? MU[Math.max(0, n)] : Math.max(0, 20 - (n - 10))) / 100;

export function poang(s: Siffror) {
  const pu = s.abt / Math.max(1, s.qKrav + s.hKrav + s.tPaverkan);
  const tg = s.abt > 0 ? (100 * s.tb) / s.abt : 0;
  const avvikelser = Math.max(0, s.qKrav - s.q) + Math.max(0, s.hKrav - s.h) + Math.max(0, s.t - T_KRAV);
  const m = mu(avvikelser);
  const f = (s.egetKapital + 0.5 * s.kassa - 100 * s.lan) / F_DELARE;
  return { pu, tg, f, avvikelser, mu: m, total: (pu + tg + f) * m };
}
