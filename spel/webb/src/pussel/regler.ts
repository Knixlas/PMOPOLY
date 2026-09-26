// Placeringspusslet (regelboken 4.3) — samma regler som motor/pussel.py, som är facit.
// Båda provas mot tester/pussel_fall.json (regler.test.ts), så de inte kan glida isär.
//
// Tomten är 16 × 16 rutor, [rad, kolumn].
//   Lager 0 — mark: grundmarken 4 × 4 mitt på tomten plus markexpansioner, kant i kant med marken.
//   Lager 1 — projekt direkt på marken (alla typer), inom marken, utan överlapp.
//   Lager 2 — bostäder ovanpå andra projekt; hela biten ska vila på lager 1 (inga hål).

export type Ruta = [number, number];
export type Form = Ruta[];
export type Lager = 0 | 1 | 2;

export interface Bit {
  id: string;
  typ: string;            // "MARK" eller projekttyp
  celler: Ruta[];
  lager: Lager;
}

export const TOMT = 16;
export const BOSTAD = new Set(['BRF', 'HYRESRÄTT']);
const GRANNAR: Ruta[] = [[1, 0], [-1, 0], [0, 1], [0, -1]];

export const nyckel = (r: number, k: number) => r * TOMT + k;
export const ruta = (n: number): Ruta => [Math.floor(n / TOMT), n % TOMT];

export const GRUNDMARK: Ruta[] = [];
for (let r = 6; r < 10; r++) for (let k = 6; k < 10; k++) GRUNDMARK.push([r, k]);

// ---------------------------------------------------------------------------- former
export function normalisera(celler: Form): Form {
  const r0 = Math.min(...celler.map(c => c[0]));
  const k0 = Math.min(...celler.map(c => c[1]));
  return celler.map(([r, k]) => [r - r0, k - k0] as Ruta).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
}

/** Formen i läge 0–7: i % 4 kvartsvarv medurs, i ≥ 4 speglad först (vänster–höger). */
export function vrid(form: Form, lage: number): Form {
  let c: Form = form.map(([r, k]) => [r, k]);
  if (lage >= 4) c = c.map(([r, k]) => [r, -k]);
  for (let i = 0; i < lage % 4; i++) c = c.map(([r, k]) => [k, -r]);
  return normalisera(c);
}

const lika = (a: Form, b: Form) => a.length === b.length && a.every((c, i) => c[0] === b[i][0] && c[1] === b[i][1]);

/** Formens olika lägen utan dubbletter, i samma ordning som motorn. */
export function lagen(form: Form): Form[] {
  const ut: Form[] = [];
  for (let i = 0; i < 8; i++) {
    const c = vrid(form, i);
    if (!ut.some(u => lika(u, c))) ut.push(c);
  }
  return ut;
}

/** Nästa läge efter ett kvartsvarv medurs, respektive spegling, uttryckt i lägesnumren 0–7. */
export const vridMedurs = (lage: number) => (lage < 4 ? (lage + 1) % 4 : 4 + ((lage + 1) % 4));
export const spegla = (lage: number) => (lage < 4 ? 4 + ((4 - lage) % 4) : (4 - (lage - 4)) % 4);

export function placera(form: Form, lage: number, rad: number, kol: number): Ruta[] {
  return vrid(form, lage).map(([r, k]) => [rad + r, kol + k]);
}

// ---------------------------------------------------------------------------- kvarteret
export interface Granskning {
  fel: Record<string, string>;
  mark: Set<number>;
  lager1: Set<number>;
}

const paTomten = (c: Ruta[]) => c.every(([r, k]) => r >= 0 && r < TOMT && k >= 0 && k < TOMT);
const nycklar = (c: Ruta[]) => c.map(([r, k]) => nyckel(r, k));
const alla = (c: number[], s: Set<number>) => c.every(n => s.has(n));
const nagon = (c: number[], s: Set<number>) => c.some(n => s.has(n));

/** De rutor i `celler` som hänger ihop (kant i kant) med `start`. */
export function sammanhangande(celler: Set<number>, start: Ruta[]): Set<number> {
  const sedda = new Set<number>();
  const ko = nycklar(start).filter(n => celler.has(n));
  while (ko.length) {
    const n = ko.pop()!;
    if (sedda.has(n)) continue;
    sedda.add(n);
    const [r, k] = ruta(n);
    for (const [dr, dk] of GRANNAR) {
      const rr = r + dr, kk = k + dk;
      if (rr >= 0 && rr < TOMT && kk >= 0 && kk < TOMT && celler.has(nyckel(rr, kk))) ko.push(nyckel(rr, kk));
    }
  }
  return sedda;
}

/** Kontrollera ett kvarter: vilka bitar bryter mot reglerna och varför. */
export function granska(bitar: Bit[], grundmark: Ruta[] = GRUNDMARK): Granskning {
  const fel: Record<string, string> = {};
  const mark = new Set(nycklar(grundmark));
  const expansioner = bitar.filter(b => b.lager === 0);
  for (const b of expansioner) {
    const c = nycklar(b.celler);
    if (!paTomten(b.celler)) fel[b.id] = 'utanför tomten';
    else if (nagon(c, mark)) fel[b.id] = 'överlappar marken';
    else c.forEach(n => mark.add(n));
  }
  const nara = sammanhangande(mark, grundmark);
  for (const b of expansioner) {
    if (!(b.id in fel) && !alla(nycklar(b.celler), nara)) fel[b.id] = 'inte kant i kant med marken';
  }
  const upptaget = new Set<number>();
  for (const b of bitar.filter(b => b.lager === 1)) {
    const c = nycklar(b.celler);
    if (!alla(c, nara)) fel[b.id] = 'utanför marken';
    else if (nagon(c, upptaget)) fel[b.id] = 'överlappar ett annat projekt';
    else c.forEach(n => upptaget.add(n));
  }
  const ovanpa = new Set<number>();
  for (const b of bitar.filter(b => b.lager === 2)) {
    const c = nycklar(b.celler);
    if (!BOSTAD.has(b.typ)) fel[b.id] = 'bara bostäder får ligga ovanpå andra projekt';
    else if (!alla(c, upptaget)) fel[b.id] = 'vilar inte helt på andra projekt';
    else if (nagon(c, ovanpa)) fel[b.id] = 'överlappar en annan bostad';
    else c.forEach(n => ovanpa.add(n));
  }
  for (const b of bitar) if (![0, 1, 2].includes(b.lager)) fel[b.id] = 'okänt lager';
  return { fel, mark: nara, lager1: upptaget };
}

/** Lagret en projektbit hamnar i om den släpps här: 1 på fri mark, 2 ovanpå projekt (bara bostäder). */
export function lagerFor(typ: string, celler: Ruta[], mark: Set<number>, lager1: Set<number>): 1 | 2 | null {
  const c = nycklar(celler);
  if (alla(c, mark) && !nagon(c, lager1)) return 1;
  if (BOSTAD.has(typ) && alla(c, lager1)) return 2;
  return null;
}
