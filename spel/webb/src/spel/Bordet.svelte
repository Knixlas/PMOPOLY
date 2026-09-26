<script lang="ts">
  // Bordet: tärningarna och korten som just slogs och drogs (helt digitalt spel).
  // Det nyaste kortet vänds upp och tärningen rullar innan den stannar på sitt värde. Det som
  // fanns när sidan öppnades visas direkt, utan animering.
  import data from '../data/pussel.json';
  import type { Visning } from './anslutning.svelte';

  let { visningar }: { visningar: Visning[] } = $props();

  const fargar = data.fargar as Record<string, { fyllning: string; ljus: string }>;
  const SKEDEFARG = { PU: '#DDA063', PL: '#1A6B9A', G: '#91B542', F: '#EF5656' };
  const G_LEKAR = /^(FAS|kultur|konsekvens|garanti)/;
  function farg(v: Visning): string {
    if (v.kort?.bild && fargar[v.kort.typ]) return fargar[v.kort.typ].fyllning;
    if (v.lek && G_LEKAR.test(v.lek)) return SKEDEFARG.G;
    if (v.skede === 'S2') return SKEDEFARG.PL;
    return SKEDEFARG[(v.skede ?? 'PU') as 'PU' | 'F'] ?? SKEDEFARG.PU;
  }
  const leknamn = (lek = '') => lek.replace(/_/g, ' ').replace(/^handelse/, 'händelse').replace(/^natverk$/, 'nätverk')
    .replace(/^omvarld$/, 'omvärld').replace(/^dd$/, 'DD');

  let forsta = $state<number | null>(null);          // allt t.o.m. detta nr fanns redan: ingen animering
  $effect(() => { if (forsta === null) forsta = visningar.at(-1)?.nr ?? 0; });

  const kort = $derived(visningar.filter(v => v.typ === 'kort').slice(-3).reverse());
  const tarningar = $derived(visningar.filter(v => v.typ === 'tarning').slice(-2).reverse());
  const ny = (v: Visning) => forsta !== null && v.nr > forsta;

  // tärningen som rullar: visar slumpade sidor en stund, sedan värdet
  let rullar = $state<Record<number, number>>({});
  const lugn = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  $effect(() => {
    for (const t of tarningar) {
      if (!ny(t) || lugn || t.nr in rullar) continue;
      rullar[t.nr] = 1 + Math.floor(Math.random() * (t.sidor ?? 6));
      let n = 0;
      const tid = setInterval(() => {
        n += 1;
        if (n >= 9) { rullar[t.nr] = -1; clearInterval(tid); }
        else rullar[t.nr] = 1 + Math.floor(Math.random() * (t.sidor ?? 6));
      }, 70);
    }
  });
  const visat = (t: Visning) => (rullar[t.nr] > 0 ? rullar[t.nr] : t.varde ?? 0);

  // ögon på en D6
  const OGON: Record<number, [number, number][]> = {
    1: [[50, 50]], 2: [[30, 30], [70, 70]], 3: [[28, 28], [50, 50], [72, 72]],
    4: [[30, 30], [70, 30], [30, 70], [70, 70]], 5: [[28, 28], [72, 28], [50, 50], [28, 72], [72, 72]],
    6: [[30, 26], [70, 26], [30, 50], [70, 50], [30, 74], [70, 74]],
  };
</script>

{#if kort.length || tarningar.length}
  <section class="bordet" aria-label="På bordet">
    <h2>På bordet</h2>
    <div class="yta">
      {#each tarningar as t (t.nr)}
        <figure class="tarning" class:rullar={rullar[t.nr] > 0} class:ny={ny(t)}
                aria-label="Tärning D{t.sidor}: {t.varde}">
          <svg viewBox="0 0 100 100" aria-hidden="true">
            {#if t.sidor === 6}
              <rect x="6" y="6" width="88" height="88" rx="16" class="d6" />
              {#each OGON[visat(t)] ?? [] as [x, y]}<circle cx={x} cy={y} r="8.5" class="oga" />{/each}
            {:else}
              <polygon points="50,3 93,27 93,73 50,97 7,73 7,27" class="d20" />
              <polygon points="50,20 78,66 22,66" class="d20-yta" />
              <text x="50" y="58" class="d20-tal">{visat(t)}</text>
            {/if}
          </svg>
          <figcaption>D{t.sidor}{t.kvarter ? ` · ${t.kvarter}` : ''}</figcaption>
        </figure>
      {/each}

      {#each kort as v (v.nr)}
        <article class="kort" class:ny={ny(v)} style="--farg:{farg(v)}">
          <header><span>{leknamn(v.lek)}</span><span class="id">{v.kort?.id}</span></header>
          {#if v.kort?.bild}<img src={v.kort.bild} alt="" />{/if}
          <h3>{v.kort?.rubrik}</h3>
          {#if v.kort?.text}<p>{v.kort.text}</p>{/if}
          {#if v.kort?.rader?.length}
            <dl>{#each v.kort.rader as [k, t]}<div><dt>{k}</dt><dd>{t}</dd></div>{/each}</dl>
          {/if}
          {#if v.kvarter}<footer>{v.kvarter}</footer>{/if}
        </article>
      {/each}
    </div>
  </section>
{/if}

<style>
  .bordet { margin: 0 0 12px; background: #3d4f47; border-radius: 6px; padding: 10px 12px 12px;
            box-shadow: inset 0 0 0 3px rgba(0, 0, 0, .12); }
  h2 { margin: 0 0 8px; font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: #e8efe9; }
  .yta { display: flex; gap: 12px; align-items: flex-start; overflow-x: auto; padding-bottom: 4px; perspective: 900px; }

  .tarning { margin: 0; flex: none; width: 76px; display: grid; gap: 4px; justify-items: center; }
  .tarning svg { width: 64px; height: 64px; filter: drop-shadow(0 4px 3px rgba(0, 0, 0, .35)); }
  .tarning figcaption { font-size: 11.5px; color: #e8efe9; text-align: center; }
  .d6 { fill: #fcf6ef; stroke: #2f3d44; stroke-width: 3; }
  .oga { fill: #2f3d44; }
  .d20 { fill: #c8453a; stroke: #7a2020; stroke-width: 3; }
  .d20-yta { fill: #e05a4d; }
  .d20-tal { font: 700 26px var(--typsnitt); fill: #fff; text-anchor: middle; font-variant-numeric: tabular-nums; }

  .kort { flex: none; width: 168px; min-height: 200px; background: var(--panel); border-radius: 8px; overflow: hidden;
          display: grid; align-content: start; box-shadow: 0 5px 10px rgba(0, 0, 0, .3); color: var(--black); }
  .kort header { background: var(--farg); color: #fff; display: flex; justify-content: space-between; gap: 6px;
                 padding: 5px 8px; font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
  .kort .id { opacity: .85; }
  .kort img { width: 90px; height: 78px; object-fit: cover; margin: 8px auto 0; display: block;
              clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%); }
  .kort h3 { margin: 8px 8px 0; font-size: 14.5px; line-height: 1.2; text-wrap: balance; }
  .kort p { margin: 4px 8px 0; font-size: 12.5px; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 6;
            line-clamp: 6; -webkit-box-orient: vertical; overflow: hidden; }
  .kort dl { margin: 6px 8px 0; display: grid; gap: 1px; font-size: 11.5px; }
  .kort dl div { display: flex; justify-content: space-between; gap: 6px; border-top: 1px solid var(--panel-mork); padding-top: 1px; }
  .kort dt { color: var(--dampad); white-space: nowrap; }
  .kort dd { margin: 0; text-align: right; font-weight: 700; }
  .kort footer { margin: 8px 8px 8px; font-size: 11.5px; color: var(--dampad); }

  @media (prefers-reduced-motion: no-preference) {
    .kort.ny { animation: vand .6s cubic-bezier(.2, .7, .3, 1) both; transform-origin: center; backface-visibility: hidden; }
    .tarning.ny { animation: kast .5s ease-out both; }
    .tarning.rullar svg { animation: rulla .14s linear infinite; }
  }
  @keyframes vand {
    0% { transform: translateY(-30px) rotateY(180deg) scale(.85); opacity: 0; }
    60% { opacity: 1; }
    100% { transform: none; opacity: 1; }
  }
  @keyframes kast { 0% { transform: translate(-40px, -30px) rotate(-120deg); opacity: 0; } 100% { transform: none; opacity: 1; } }
  @keyframes rulla { 0% { transform: rotate(0); } 50% { transform: rotate(12deg) scale(.96); } 100% { transform: rotate(0); } }
</style>
