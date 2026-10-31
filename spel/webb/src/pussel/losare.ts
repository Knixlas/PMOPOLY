// Lösaren — samma sökning som motor/pussel.py: losa (flest projekt, sedan störst yta).
// Används för ledtråden "Går det?" och "Lägg åt mig". Rutorna i marken blir bitar i en BigInt.
import { BOSTAD, lagen, type Form, type Lager, type Ruta } from './regler';

export interface ProjektIn { id: string; typ: string; form: Form }
export interface Losning {
  placeringar: Record<string, { celler: Ruta[]; lager: Lager }>;
  fullstandig: boolean;           // false = avbröts vid gränsen, svaret är det bästa som hittats
}

const antalEttor = (m: bigint) => {
  let n = 0;
  while (m) { m &= m - 1n; n++; }
  return n;
};

function antalSomRyms(storlekar: number[], yta: number) {
  let n = 0;
  for (const s of [...storlekar].sort((a, b) => a - b)) {
    if (s > yta) break;
    yta -= s;
    n++;
  }
  return n;
}

function platser(form: Form, index: Map<string, bigint>, rutor: Ruta[]): bigint[] {
  const rader = rutor.map(c => c[0]), kolumner = rutor.map(c => c[1]);
  const [r0, r1, k0, k1] = [Math.min(...rader), Math.max(...rader), Math.min(...kolumner), Math.max(...kolumner)];
  const ut = new Set<bigint>();
  for (const c of lagen(form)) {
    for (let r = r0; r <= r1; r++) {
      for (let k = k0; k <= k1; k++) {
        let mask = 0n, ok = true;
        for (const [dr, dk] of c) {
          const b = index.get(`${r + dr},${k + dk}`);
          if (b === undefined) { ok = false; break; }
          mask |= b;
        }
        if (ok) ut.add(mask);
      }
    }
  }
  return [...ut].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

export function losa(mark: Ruta[], projekt: ProjektIn[], opt: { alla?: boolean; grans?: number; ms?: number } = {}): Losning {
  const allaMaste = opt.alla ?? false;
  const grans = opt.grans ?? 300_000;
  const slut = opt.ms ? performance.now() + opt.ms : Infinity;
  const rutor = [...mark].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const index = new Map<string, bigint>(rutor.map((c, i) => [`${c[0]},${c[1]}`, 1n << BigInt(i)]));
  const hela = (1n << BigInt(rutor.length)) - 1n;
  const ordning = projekt.map((p, i) => ({ ...p, i })).sort((a, b) => b.form.length - a.form.length || a.i - b.i);
  const storlek = new Map(ordning.map(p => [p.id, p.form.length]));
  const plats = new Map(ordning.map(p => [p.id, platser(p.form, index, rutor)]));
  let bast = { n: -1, yta: -1, plac: new Map<string, [bigint, Lager]>() };
  let steg = 0, stopp = false;

  const spara = (plac: Map<string, [bigint, Lager]>) => {
    const n = plac.size;
    let yta = 0;
    for (const id of plac.keys()) yta += storlek.get(id)!;
    if (n > bast.n || (n === bast.n && yta > bast.yta)) bast = { n, yta, plac: new Map(plac) };
  };
  const rakna = () => {
    steg++;
    if (steg > grans || (steg % 2048 === 0 && performance.now() > slut)) stopp = true;
    return stopp;
  };

  const fas2 = (uppe: typeof ordning, plac: Map<string, [bigint, Lager]>, underlag: bigint, i: number): void => {
    if (rakna()) return;
    if (i === uppe.length) { spara(plac); return; }
    const kvar = uppe.slice(i).map(p => storlek.get(p.id)!);
    if (plac.size + antalSomRyms(kvar, antalEttor(underlag)) < bast.n) return;
    const id = uppe[i].id;
    for (const m of plats.get(id)!) {
      if ((m & underlag) === m) {
        plac.set(id, [m, 2]);
        fas2(uppe, plac, underlag & ~m, i + 1);
        plac.delete(id);
      }
    }
    if (!allaMaste) fas2(uppe, plac, underlag, i + 1);
  };

  const fas1 = (i: number, fritt: bigint, plac: Map<string, [bigint, Lager]>, uppe: typeof ordning): void => {
    if (rakna()) return;
    if (allaMaste && bast.n === ordning.length) return;
    const kvar = ordning.slice(i);
    const friYta = antalEttor(fritt);
    const ovriga = kvar.filter(p => !BOSTAD.has(p.typ)).map(p => p.form.length);
    const bostader = [...kvar.filter(p => BOSTAD.has(p.typ)).map(p => p.form.length), ...uppe.map(p => storlek.get(p.id)!)];
    const tak = plac.size + antalSomRyms(ovriga, friYta) + antalSomRyms(bostader, friYta + rutor.length);
    if (tak < bast.n || (allaMaste && tak < ordning.length)) return;
    if (i === ordning.length) {
      fas2(uppe, new Map(plac), hela & ~fritt, 0);
      return;
    }
    const p = ordning[i];
    for (const m of plats.get(p.id)!) {
      if ((m & fritt) === m) {
        plac.set(p.id, [m, 1]);
        fas1(i + 1, fritt & ~m, plac, uppe);
        plac.delete(p.id);
      }
    }
    if (BOSTAD.has(p.typ)) fas1(i + 1, fritt, plac, [...uppe, p]);
    if (!allaMaste) fas1(i + 1, fritt, plac, uppe);
  };

  fas1(0, hela, new Map(), []);
  const placeringar: Losning['placeringar'] = {};
  if (!(allaMaste && bast.n < ordning.length)) {
    for (const [id, [m, lager]] of bast.plac) {
      placeringar[id] = { celler: rutor.filter((c, i) => (m >> BigInt(i)) & 1n), lager };
    }
  }
  return { placeringar, fullstandig: !stopp };
}
