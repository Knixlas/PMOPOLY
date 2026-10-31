import { describe, expect, it } from 'vitest';
import { mu, poang } from './poang';

describe('slutpoängen', () => {
  it('Mu följer tabellen i 10.2', () => {
    expect(mu(0)).toBe(1);
    expect(mu(4)).toBe(0.44);
    expect(mu(15)).toBe(0.15);
  });
  it('räknar som motorn', () => {
    const p = poang({ abt: 300, qKrav: 11, hKrav: 11, tPaverkan: 0, tb: 18, q: 10, h: 11, t: 13,
                      egetKapital: 250, kassa: 60, lan: 0 });
    expect(p.pu).toBeCloseTo(300 / 22);
    expect(p.tg).toBeCloseTo(6);
    expect(p.avvikelser).toBe(2);
    expect(p.f).toBeCloseTo(280 / 30);
    expect(p.total).toBeCloseTo((300 / 22 + 6 + 280 / 30) * 0.65);
  });
});
