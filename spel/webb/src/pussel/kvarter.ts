// Kvarteret i gränssnittet: vilka bitar som finns, var de ligger och vad som händer när man
// lyfter eller släpper en bit. Reglerna själva finns i regler.ts.
import { BOSTAD, TOMT, granska, lagerFor, nyckel, ruta, type Bit, type Form, type Lager, type Ruta } from './regler';

export interface Del {
  id: string;
  namn: string;
  typ: string;            // "MARK" eller projekttyp
  form: Form;
  bta?: number;
  bya?: number;
  bild?: string | null;
}

export interface Lagd {
  id: string;
  lage: number;           // 0–7, se regler.vrid
  rad: number;            // formens övre vänstra hörn (i läget) på tomten
  kol: number;
  lager: Lager;
}

/** Formen i ett läge, i samma ordning som formens rutor (så att "rutan man håller i" följer med). */
export function orienterad(form: Form, lage: number): Ruta[] {
  let c: Ruta[] = form.map(([r, k]) => [r, k]);
  if (lage >= 4) c = c.map(([r, k]) => [r, -k]);
  for (let i = 0; i < lage % 4; i++) c = c.map(([r, k]) => [k, -r]);
  const r0 = Math.min(...c.map(x => x[0])), k0 = Math.min(...c.map(x => x[1]));
  return c.map(([r, k]) => [r - r0, k - k0]);
}

export const cellerFor = (form: Form, lage: number, rad: number, kol: number): Ruta[] =>
  orienterad(form, lage).map(([r, k]) => [rad + r, kol + k]);

export function somBitar(lagda: Lagd[], delar: Map<string, Del>): Bit[] {
  return lagda.map(l => {
    const d = delar.get(l.id)!;
    return { id: l.id, typ: d.typ, celler: cellerFor(d.form, l.lage, l.rad, l.kol), lager: l.lager };
  });
}

export interface Prov {
  lager: Lager | null;     // null = får inte ligga här
  daliga: Set<number>;     // rutor som bryter mot reglerna (för rödmarkering)
  skal: string;            // förklaring när det inte går
}

/** Kan delen läggas på de här rutorna, givet allt annat som ligger (utom delen själv)? */
export function prova(del: Del, celler: Ruta[], ovriga: Lagd[], delar: Map<string, Del>): Prov {
  const varld = somBitar(ovriga, delar);
  const n = celler.map(([r, k]) => nyckel(r, k));
  const utanfor = new Set(celler.filter(([r, k]) => r < 0 || r >= TOMT || k < 0 || k >= TOMT).map(([r, k]) => nyckel(r, k)));
  if (del.typ === 'MARK') {
    const g = granska([...varld, { id: del.id, typ: 'MARK', celler, lager: 0 }]);
    const skal = g.fel[del.id];
    if (!skal) return { lager: 0, daliga: new Set(), skal: '' };
    const mark = granska(varld).mark;
    const krock = new Set(n.filter(x => mark.has(x)));
    const daliga = utanfor.size ? utanfor : krock.size ? krock : new Set(n);
    return { lager: null, daliga, skal: skal === 'inte kant i kant med marken' ? 'Markexpansionen ska ligga kant i kant med marken.' : `Markexpansionen ${skal}.` };
  }
  const g = granska(varld);
  const ovanpa = new Set<number>();
  for (const b of varld) if (b.lager === 2) b.celler.forEach(([r, k]) => ovanpa.add(nyckel(r, k)));
  const lager = lagerFor(del.typ, celler, g.mark, g.lager1);
  if (lager === 2 && n.some(x => ovanpa.has(x))) {
    return { lager: null, daliga: new Set(n.filter(x => ovanpa.has(x))), skal: 'Två bostäder kan inte ligga på samma ställe.' };
  }
  if (lager !== null) return { lager, daliga: new Set(), skal: '' };
  // varför inte? markera de rutor som felar
  const paProjekt = n.filter(x => g.lager1.has(x));
  const paFriMark = n.filter(x => g.mark.has(x) && !g.lager1.has(x));
  const utanforMark = n.filter(x => !g.mark.has(x));
  if (utanforMark.length && !paProjekt.length) {
    return { lager: null, daliga: new Set(utanforMark), skal: 'Projekt ska ligga på marken (grundmark eller markexpansion).' };
  }
  if (!BOSTAD.has(del.typ)) {
    return { lager: null, daliga: new Set([...paProjekt, ...utanforMark]),
      skal: 'Bara bostäder (BRF och hyresrätt) får ligga ovanpå andra projekt.' };
  }
  const daliga = paProjekt.length >= paFriMark.length ? [...paFriMark, ...utanforMark] : [...paProjekt, ...utanforMark];
  return { lager: null, daliga: new Set(daliga),
    skal: 'En bostad ovanpå ska vila helt på andra projekt, utan hål. Annars ska den ligga helt på fri mark.' };
}

/** Går det att lyfta biten utan att något annat blir fel (t.ex. en bostad som vilar på den)? */
export function kanLyfta(id: string, lagda: Lagd[], delar: Map<string, Del>): string | null {
  const fore = granska(somBitar(lagda, delar)).fel;
  const efter = granska(somBitar(lagda.filter(l => l.id !== id), delar)).fel;
  const nya = Object.keys(efter).filter(k => !(k in fore));
  if (!nya.length) return null;
  const vad = delar.get(nya[0])!;
  return delar.get(id)!.typ === 'MARK'
    ? `Flytta först ${vad.namn}, som ligger på eller hänger ihop via den här markbiten.`
    : `Flytta först ${vad.namn}, som vilar på det här projektet.`;
}

export const rutaFran = ruta;
