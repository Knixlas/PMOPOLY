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
    ? (paBordet.length ? 'Korten når ingen nivå – de går tillbaka till handen och fasen blir Negativt.' : 'Välj kort tills en nivå nås.')
    : `Ni når ${nadd} (${effekt(nadd)}). De valda korten förbrukas.`);

  // kompetenserna som FAS-kortet frågar efter; bara kort med någon av dem visas (om man inte vill se alla)
  const relevanta = $derived(new Set((vy.nivaer ?? []).flatMap(([, kr]: any) => Object.keys(kr))));
  const nytta = (a: any) => Object.entries(a.komp ?? {}).filter(([k]) => relevanta.has(k)).reduce((s, [, n]) => s + (n as number), 0);
  let visaAlla = $state(false);
  const handen = $derived([...iHanden].filter((a: any) => visaAlla || nytta(a) > 0).sort((x: any, y: any) => nytta(y) - nytta(x)));
  const utan = $derived(iHanden.filter((a: any) => nytta(a) === 0).length);
  const kortNamn = (a: any) => a.kort?.rubrik ?? a.text;
</script>

<div class="fasspel">
  <div class="topp">
    {#if vy.fas_kort}<Kort kort={vy.fas_kort} lek={vy.fas_kort.lek ?? 'FAS'} skede="G" stor />{/if}
    <table>
      <thead><tr><th>Nivå</th><th>Krav (valt / krav)</th><th>Effekt</th></tr></thead>
      <tbody>
        {#each vy.nivaer ?? [] as [n, kr]}
          <tr class:nadd={n === nadd} class:mojlig={nar(kr)}>
            <td>{n}</td>
            <td>
              {#each Object.entries(kr) as [k, v], j}{j ? ' · ' : ''}<span class:uppfyllt={(summa[k] ?? 0) >= (v as number)} title={KOMP[k]}>{k} {summa[k] ?? 0}/{v}</span>{:else}inget{/each}
            </td>
            <td>{effekt(n)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <section class="bord" aria-label="Valda kort">
    <h3>Valda kort · {paBordet.length}</h3>
    {#if paBordet.length}
      <ul class="rader">
        {#each paBordet as a (a.i)}
          <li><button type="button" class="rad vald" onclick={() => vaxla(a.i)} disabled={skickar} aria-pressed="true">
            <span class="bock">✓</span><span class="namn">{kortNamn(a)}</span>
            <span class="komp">{#each Object.entries(a.komp ?? {}) as [k, n], j}{j ? ' · ' : ''}<span class:rel={relevanta.has(k)}>{k} {n}</span>{/each}</span>
          </button></li>
        {/each}
      </ul>
    {/if}
    <p class="kvitt" class:bra={nadd !== 'Negativt'}>{kvittText}</p>
    <div class="knappar">
      <button type="button" class="las" disabled={skickar} onclick={() => svara({ flera: valda })}>
        {valda.length ? `Lås spelade kort (${valda.length})` : 'Spela inga kort'}
      </button>
      {#if valda.length}<button type="button" class="sekundar" disabled={skickar} onclick={() => (valda = [])}>Välj bort alla</button>{/if}
    </div>
  </section>

  <section aria-label="Er hand">
    <h3>Er hand · {iHanden.length} kort{visaAlla ? '' : ` · ${handen.length} kan hjälpa`}</h3>
    <ul class="rader">
      {#each handen as a (a.i)}
        <li><button type="button" class="rad" class:svag={nytta(a) === 0} onclick={() => vaxla(a.i)} disabled={skickar} aria-pressed="false">
          <span class="bock"></span><span class="namn">{kortNamn(a)}</span>
          <span class="komp">{#each Object.entries(a.komp ?? {}) as [k, n], j}{j ? ' · ' : ''}<span class:rel={relevanta.has(k)}>{k} {n}</span>{:else}ingen kompetens{/each}</span>
        </button></li>
      {/each}
    </ul>
    {#if utan}
      <button type="button" class="lank" onclick={() => (visaAlla = !visaAlla)}>
        {visaAlla ? 'Visa bara kort som kan hjälpa' : `Visa även ${utan} kort utan de kompetenser fasen kräver`}
      </button>
    {/if}
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
  .uppfyllt { color: var(--ok); font-weight: 700; }
  .bord { background: #3d4f47; color: #e8efe9; border-radius: 6px; padding: 10px 12px; display: grid; gap: 8px;
          position: sticky; bottom: 0; z-index: 3; }
  h3 { margin: 0; font-size: 13px; letter-spacing: .1em; text-transform: uppercase; }
  .kvitt { margin: 0; font-size: 14.5px; }
  .kvitt.bra { color: #bfe3a6; font-weight: 700; }
  .rader { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; max-height: 50vh; overflow-y: auto; }
  .bord .rader { max-height: 30vh; }
  .rad { width: 100%; display: grid; grid-template-columns: 22px minmax(0, 1fr) auto; gap: 8px; align-items: baseline;
         padding: 7px 10px; border-radius: 4px; border: 1px solid var(--linje-stark); background: #fff; color: var(--black);
         font: inherit; text-align: left; cursor: pointer; }
  .rad:hover:not(:disabled) { border-color: var(--black); }
  .rad.vald { background: #e6f0dc; border-color: var(--ok); }
  .rad.svag { opacity: .6; }
  .bock { color: var(--ok); font-weight: 700; }
  .namn { font-weight: 600; font-size: 14.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .komp { font-size: 13px; color: var(--dampad); white-space: nowrap; font-variant-numeric: tabular-nums; }
  .komp .rel { color: var(--black); font-weight: 700; }
  @media (max-width: 520px) {
    .rad { grid-template-columns: 22px minmax(0, 1fr); }
    .komp { grid-column: 2; white-space: normal; }
  }
  .knappar { display: flex; flex-wrap: wrap; gap: 8px; }
  .las { font: inherit; font-weight: 700; font-size: 16px; padding: 10px 18px; border-radius: 4px; border: 0; background: var(--pu); color: var(--black); cursor: pointer; }
  .sekundar { font: inherit; padding: 10px 14px; border-radius: 4px; border: 1px solid #e8efe9; background: transparent; color: #e8efe9; cursor: pointer; }
  .lank { justify-self: start; background: none; border: 0; padding: 4px 0; font: inherit; color: var(--pu-mork); font-weight: 700; text-decoration: underline; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
  button:focus-visible { outline: 3px solid var(--pu); outline-offset: 2px; }
</style>
