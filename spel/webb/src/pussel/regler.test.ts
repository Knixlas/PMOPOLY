// Webbklientens regler och lösare mot facit från motorn (tester/pussel_fall.json, skapad av
// verktyg/exportera_webbdata.py med motor/pussel.py).
import { describe, expect, it } from 'vitest';
import fall from '../../../../tester/pussel_fall.json';
import data from '../data/pussel.json';
import { granska, lagen, lagerFor, nyckel, spegla, vrid, vridMedurs, type Bit, type Form, type Ruta } from './regler';
import { losa } from './losare';

const alla = [...data.projekt, ...data.markexpansioner];
const form = new Map(alla.map(p => [p.id, p.form as Form]));
const typ = new Map(data.projekt.map(p => [p.id, p.typ]));

describe('samma svar som motorn', () => {
  it('lägen', () => {
    for (const [id, facit] of Object.entries(fall.lagen)) expect(lagen(form.get(id)!), id).toEqual(facit);
  });

  it('granskning', () => {
    for (const f of fall.granska) {
      const g = granska(f.bitar as Bit[]);
      expect(Object.keys(g.fel).sort()).toEqual([...f.fel].sort());
    }
  });

  it('lösaren', () => {
    for (const f of fall.losa.slice(0, 15)) {
      const proj = f.projekt.map(id => ({ id, typ: typ.get(id)!, form: form.get(id)! }));
      const l = losa(f.mark as Ruta[], proj);
      expect(l.fullstandig).toBe(true);
      const plac = Object.values(l.placeringar);
      expect([plac.length, plac.reduce((s, p) => s + p.celler.length, 0)]).toEqual([f.antal, f.yta]);
      const kvarter: Bit[] = [{ id: 'mark', typ: 'MARK', lager: 0,
        celler: (f.mark as Ruta[]).filter(([r, k]) => !(r >= 6 && r < 10 && k >= 6 && k < 10)) }];
      for (const [id, p] of Object.entries(l.placeringar)) kvarter.push({ id, typ: typ.get(id)!, ...p });
      expect(granska(kvarter).fel).toEqual({});
      expect(Object.keys(losa(f.mark as Ruta[], proj, { alla: true }).placeringar).length > 0).toBe(f.alla);
    }
  });
});

describe('rotera och spegla', () => {
  const L: Form = [[0, 0], [1, 0], [2, 0], [2, 1]];
  it('fyra kvartsvarv är ett helt varv, två speglingar tar ut varandra', () => {
    for (let lage = 0; lage < 8; lage++) {
      let l = lage;
      for (let i = 0; i < 4; i++) l = vridMedurs(l);
      expect(l).toBe(lage);
      expect(spegla(spegla(lage))).toBe(lage);
    }
  });
  it('spegling vänder vänster–höger så som den syns', () => {
    for (let lage = 0; lage < 8; lage++) {
      const fore = vrid(L, lage), efter = vrid(L, spegla(lage));
      const bredd = Math.max(...fore.map(c => c[1]));
      const speglad = fore.map(([r, k]) => [r, bredd - k]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      expect(efter).toEqual(speglad);
    }
  });
});

describe('hålregeln', () => {
  it('bostad måste vila helt på projekt', () => {
    const mark = new Set<number>();
    for (let r = 6; r < 10; r++) for (let k = 6; k < 10; k++) mark.add(nyckel(r, k));
    const under = new Set([nyckel(6, 6), nyckel(6, 7)]);
    expect(lagerFor('BRF', [[6, 6], [6, 7]], mark, under)).toBe(2);
    expect(lagerFor('BRF', [[6, 7], [6, 8]], mark, under)).toBe(null);
    expect(lagerFor('KONTOR', [[6, 6]], mark, under)).toBe(null);
  });
});
