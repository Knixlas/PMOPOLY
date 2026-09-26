<script lang="ts">
  // Provsida för pusslet: ett slumpat kvarter med godkända projekt och markexpansioner,
  // som efter nämnden i Skede 1 (regelboken 4.3).
  import data from './data/pussel.json';
  import Pussel from './pussel/Pussel.svelte';
  import { cellerFor, prova, type Del, type Lagd } from './pussel/kvarter';
  import { losa } from './pussel/losare';
  import { GRUNDMARK, nyckel, type Form, type Ruta } from './pussel/regler';

  const projekt: Del[] = data.projekt.map(p => ({ ...p, form: p.form as Form }));
  const mark: Del[] = data.markexpansioner.map(m => ({ ...m, form: m.form as Form }));

  function slump(fro: number) {                     // mulberry32: samma frö ger samma pussel
    return () => {
      fro |= 0; fro = (fro + 0x6d2b79f5) | 0;
      let t = Math.imul(fro ^ (fro >>> 15), 1 | fro);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function valj<T>(lista: T[], n: number, r: () => number): T[] {
    const kopia = [...lista];
    for (let i = kopia.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [kopia[i], kopia[j]] = [kopia[j], kopia[i]]; }
    return kopia.slice(0, n);
  }

  let antal = $state(6);
  let fro = $state(7);
  let pussel = $derived(bygg(fro, antal));

  function bygg(fro: number, antal: number) {
    const r = slump(fro);
    const valda = valj(projekt, antal, r);
    const exp = valj(mark, 2, r);
    const delar = [...exp, ...valda];
    const byMap = new Map(delar.map(d => [d.id, d]));
    // exempelläge: första markexpansionen och två projekt ligger redan, resten finns i handen
    const start: Lagd[] = [];
    const e = exp[0];
    lagt: for (const [rad, kol] of [[10, 6], [6, 10], [3, 7], [7, 3], [10, 8]] as Ruta[]) {
      for (let lage = 0; lage < 8; lage++) {
        const p = prova(e, cellerFor(e.form, lage, rad, kol), start, byMap);
        if (p.lager === 0) { start.push({ id: e.id, lage, rad, kol, lager: 0 }); break lagt; }
      }
    }
    const markNu: Ruta[] = [...GRUNDMARK];
    for (const l of start) markNu.push(...cellerFor(e.form, l.lage, l.rad, l.kol));
    const l = losa(markNu, valda.map(p => ({ id: p.id, typ: p.typ, form: p.form })), { ms: 800 });
    for (const [id, p] of Object.entries(l.placeringar).slice(0, 2)) {
      const d = byMap.get(id)!;
      const rad = Math.min(...p.celler.map(c => c[0])), kol = Math.min(...p.celler.map(c => c[1]));
      const mal = new Set(p.celler.map(([a, b]) => nyckel(a, b)));
      for (let lage = 0; lage < 8; lage++) {
        if (cellerFor(d.form, lage, rad, kol).every(([a, b]) => mal.has(nyckel(a, b)))) {
          start.push({ id, lage, rad, kol, lager: p.lager });
          break;
        }
      }
    }
    return { delar, start };
  }

  function nytt() {
    fro = Math.floor(Math.random() * 1e9);
  }
</script>

<header class="topp">
  <div class="titel">
    <span class="skede">PU · Projektutveckling · 4.3 Placering</span>
    <h1>Kvarterspusslet</h1>
    <p>Nämnden har godkänt dina projekt. Lägg dem på marken så att kvarteret går ihop. Bostäder får ligga ovanpå andra projekt om hela biten vilar på dem.</p>
  </div>
  <div class="nytt">
    <label for="antal">Projekt</label>
    <select id="antal" bind:value={antal}>
      {#each [4, 5, 6, 7, 8] as n}<option value={n}>{n}</option>{/each}
    </select>
    <button type="button" onclick={nytt}>Nytt pussel</button>
  </div>
</header>

<main>
  {#key pussel}
    <Pussel delar={pussel.delar} start={pussel.start} fargar={data.fargar} />
  {/key}
</main>

<footer>
  ÅKEPOL · formerna och färgerna är brickornas, ur kortdata. Samma regler som spelmotorn.
</footer>

<style>
  .topp {
    display: flex; flex-wrap: wrap; gap: 16px 32px; align-items: end; justify-content: space-between;
    padding-block: 20px 16px; border-bottom: 3px solid var(--pu); margin-bottom: 18px;
  }
  .titel { max-width: 62ch; display: grid; gap: 4px; }
  .skede { font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--pu-mork); }
  h1 { margin: 0; font-size: clamp(28px, 5vw, 40px); font-weight: 700; letter-spacing: .01em; text-wrap: balance; color: var(--black); }
  .titel p { margin: 0; font-size: 15.5px; line-height: 1.45; }
  .nytt { display: flex; gap: 8px; align-items: center; }
  .nytt label { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; font-weight: 700; }
  select, .nytt button {
    font: inherit; font-weight: 600; font-size: 15px; padding: 8px 12px; border-radius: 4px;
    border: 1px solid var(--linje-stark); background: var(--panel); color: var(--black);
  }
  .nytt button { background: var(--pu); border-color: var(--pu); color: var(--black); cursor: pointer; }
  .nytt button:hover { background: var(--pu-mork); border-color: var(--pu-mork); color: #fff; }
  select:focus-visible, .nytt button:focus-visible { outline: 3px solid var(--black); outline-offset: 2px; }
  footer { margin-top: 28px; padding-block: 12px 20px; font-size: 13px; color: var(--dampad); border-top: 1px solid var(--linje-stark); }
</style>
