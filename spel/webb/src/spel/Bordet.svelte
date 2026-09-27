<script lang="ts">
  // Bordet: tärningarna och korten som just slogs och drogs (helt digitalt spel).
  // Det nyaste kortet vänds upp och tärningen rullar innan den stannar på sitt värde. Det som
  // fanns när sidan öppnades visas direkt, utan animering.
  import Kort from './Kort.svelte';
  import type { Visning } from './anslutning.svelte';

  let { visningar: alla, skede = null, jag = null }: { visningar: Visning[]; skede?: string | null; jag?: string | null } = $props();
  // bara det nuvarande skedets slag och kort (yieldkorten dras t.ex. redan vid uppställningen), och bara
  // ert kvarters – plus det som gäller alla (t.ex. omvärldskort). Bordsenheten (jag = null) ser allt.
  const visningar = $derived(alla.filter(v => (!skede || !v.skede || v.skede === skede) && (!jag || !v.kvarter || v.kvarter === jag)));

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
          <figcaption>D{t.sidor}{!jag && t.kvarter ? ` · ${t.kvarter}` : ''}</figcaption>
        </figure>
      {/each}

      {#each kort as v (v.nr)}
        <Kort kort={v.kort!} lek={v.lek} skede={v.skede} ny={ny(v)} kvarter={jag ? null : v.kvarter} />
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

  @media (prefers-reduced-motion: no-preference) {
    .tarning.ny { animation: kast .5s ease-out both; }
    .tarning.rullar svg { animation: rulla .14s linear infinite; }
  }
  @keyframes kast { 0% { transform: translate(-40px, -30px) rotate(-120deg); opacity: 0; } 100% { transform: none; opacity: 1; } }
  @keyframes rulla { 0% { transform: rotate(0); } 50% { transform: rotate(12deg) scale(.96); } 100% { transform: rotate(0); } }
</style>
