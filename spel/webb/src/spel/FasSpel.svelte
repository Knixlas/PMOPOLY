<script lang="ts">
  // Genomförandet (7.5): tryck på kompetenskort i handen så läggs de på bordet. Summan på bordet visar
  // vilken nivå på FAS-kortet ni når. "Lås spelade kort" skickar valet; tills dess kan korten tas tillbaka.
  import Kort from './Kort.svelte';
  import type { Fraga, Svar } from './anslutning.svelte';

  let { fraga, svara, skickar = false }: { fraga: Fraga; svara: (s: Svar) => void; skickar?: boolean } = $props();
  const vy = $derived(fraga.vy as any);

  const KOMP: Record<string, string> = { STA: 'Stabilitet', KOM: 'Kommunikation', SAM: 'Samarbete', NOG: 'Noggrannhet', INN: 'Innovation', ABM: 'Arbetsmiljö' };
  let valda = $state<number[]>([]);
  $effect.pre(() => { void fraga.nr; valda = []; });

  const alla = $derived((vy.alternativ ?? []).map((a: any, i: number) => ({ ...a, i })));
  const paBordet = $derived(alla.filter((a: any) => valda.includes(a.i)));
  const iHanden = $derived(alla.filter((a: any) => !valda.includes(a.i)));
  const summa = $derived.by(() => {
    const s: Record<string, number> = {};
    for (const a of paBordet) for (const [k, n] of Object.entries(a.komp ?? {})) s[k] = (s[k] ?? 0) + (n as number);
    return s;
  });
  const nar = (kr: Record<string, number>) => Object.entries(kr).every(([k, n]) => (summa[k] ?? 0) >= n);
  const nadd = $derived.by(() => {
    let bast = 'Negativt';
    for (const [n, kr] of vy.nivaer ?? []) if (nar(kr)) bast = n;
    return bast;
  });
  const effekt = (n: string) => (vy.nivaer ?? []).find((x: any) => x[0] === n)?.[2] || 'ingen effekt';
  const kravText = (kr: Record<string, number>) => Object.entries(kr).map(([k, n]) => `${k} ${n}`).join(', ') || 'inget';
  const vaxla = (i: number) => (valda = valda.includes(i) ? valda.filter(x => x !== i) : [...valda, i]);
  const kvittText = $derived(nadd === 'Negativt'
    ? (paBordet.length ? 'Korten når ingen nivå – de går tillbaka till handen och fasen blir Negativt.' : 'Inga kort på bordet: fasen blir Negativt.')
    : `Ni når ${nadd} (${effekt(nadd)}). Korten på bordet förbrukas.`);
</script>

<div class="fasspel">
  <div class="topp">
    {#if vy.fas_kort}<Kort kort={vy.fas_kort} lek={vy.fas_kort.lek ?? 'FAS'} skede="G" stor />{/if}
    <table>
      <thead><tr><th>Nivå</th><th>Krav</th><th>Effekt</th></tr></thead>
      <tbody>
        {#each vy.nivaer ?? [] as [n, kr]}
          <tr class:nadd={n === nadd} class:mojlig={nar(kr)}><td>{n}</td><td>{kravText(kr)}</td><td>{effekt(n)}</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <section class="bord" aria-label="Spelade kort">
    <h3>På bordet · {paBordet.length} kort</h3>
    <p class="summa">
      {#if Object.keys(summa).length}
        {#each Object.entries(summa) as [k, n]}<span>{KOMP[k] ?? k} <strong>{n}</strong></span>{/each}
      {:else}Tryck på kort i handen för att lägga dem här.{/if}
    </p>
    <div class="rad">
      {#each paBordet as a (a.i)}
        <button type="button" class="kortknapp" onclick={() => vaxla(a.i)} disabled={skickar} aria-label="Ta tillbaka {a.text}">
          <Kort kort={a.kort} lek="kompetens" skede="S2" />
        </button>
      {/each}
    </div>
    <p class="kvitt" class:bra={nadd !== 'Negativt'}>{kvittText}</p>
    <div class="knappar">
      <button type="button" class="las" disabled={skickar} onclick={() => svara({ flera: valda })}>
        {valda.length ? `Lås spelade kort (${valda.length})` : 'Spela inga kort'}
      </button>
      {#if valda.length}<button type="button" class="sekundar" disabled={skickar} onclick={() => (valda = [])}>Ta tillbaka alla</button>{/if}
    </div>
  </section>

  <section aria-label="Er hand">
    <h3>Er hand · {iHanden.length} kort</h3>
    <div class="rad">
      {#each iHanden as a (a.i)}
        <button type="button" class="kortknapp" onclick={() => vaxla(a.i)} disabled={skickar} aria-label="Lägg {a.text} på bordet">
          <Kort kort={a.kort} lek="kompetens" skede="S2" />
        </button>
      {/each}
    </div>
  </section>
</div>

<style>
  .fasspel { display: grid; gap: 12px; min-width: 0; }
  .fasspel > * { min-width: 0; }
  .topp { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; }
  table { border-collapse: collapse; font-size: 14px; flex: 1 1 260px; }
  th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--panel-mork); }
  tr.mojlig td:first-child::after { content: ' ✓'; color: var(--ok); }
  tr.nadd td { background: #e6f0dc; font-weight: 700; }
  .bord { background: #3d4f47; color: #e8efe9; border-radius: 6px; padding: 10px 12px; display: grid; gap: 8px; }
  h3 { margin: 0; font-size: 13px; letter-spacing: .1em; text-transform: uppercase; }
  .summa { margin: 0; display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 14px; }
  .kvitt { margin: 0; font-size: 14.5px; }
  .kvitt.bra { color: #bfe3a6; font-weight: 700; }
  .rad { display: flex; gap: 10px; overflow-x: auto; padding: 2px 2px 8px; min-height: 40px; }
  .kortknapp { padding: 0; border: 0; background: none; cursor: pointer; border-radius: 8px; text-align: left; font: inherit; color: inherit; }
  .kortknapp:focus-visible { outline: 3px solid var(--pu); outline-offset: 2px; }
  .kortknapp:hover:not(:disabled) { transform: translateY(-3px); }
  .knappar { display: flex; flex-wrap: wrap; gap: 8px; }
  .las { font: inherit; font-weight: 700; font-size: 16px; padding: 10px 18px; border-radius: 4px; border: 0; background: var(--pu); color: var(--black); cursor: pointer; }
  .sekundar { font: inherit; padding: 10px 14px; border-radius: 4px; border: 1px solid #e8efe9; background: transparent; color: #e8efe9; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
</style>
