<script lang="ts">
  // En enhet i ett parti: välj vilket kvarter ni är, svara på era frågor, följ läget.
  import { onDestroy } from 'svelte';
  import { Anslutning, hamtaLage, type Lage as LageT } from '../spel/anslutning.svelte';
  import Bordet from '../spel/Bordet.svelte';
  import Brade from '../spel/Brade.svelte';
  import Spelledare from '../spel/Spelledare.svelte';
  import Fraga from '../spel/Fraga.svelte';
  import Lage from '../spel/Lage.svelte';

  let { id, kvarter }: { id: string; kvarter?: string } = $props();

  let forhand = $state<LageT | null>(null);
  let saknas = $state(false);
  let anslutning = $state<Anslutning | null>(null);
  let kopierat = $state(false);

  $effect(() => {
    if (kvarter) {
      const a = new Anslutning(id, kvarter);
      anslutning = a;
      return () => a.stang();
    }
    hamtaLage(id).then(l => { forhand = l; saknas = !l; });
  });
  onDestroy(() => anslutning?.stang());

  const lage = $derived(anslutning?.lage ?? null);
  const fraga = $derived(lage?.fraga ?? null);
  const minTur = $derived(!!fraga?.min);
  const lank = $derived(`${location.origin}${location.pathname}#/parti/${id}`);
  // brädet visas i Skede 1, men inte medan man själv lägger pusslet (då behövs hela bredden)
  const visaBrade = $derived(lage?.bild?.skede === 'PU' && !(minTur && ['pussel', 'markexpansion'].includes(fraga?.vy.typ ?? '')));
  const skedenamn: Record<string, string> = { PU: 'Skede 1', S2: 'Skede 2', F: 'Förvaltning' };

  async function kopiera() {
    try { await navigator.clipboard.writeText(lank); kopierat = true; setTimeout(() => (kopierat = false), 2000); }
    catch { kopierat = false; }
  }

  const resultat = $derived(lage?.resultat
    ? [...lage.resultat].sort((a: any, b: any) => (b.total ?? b.F) - (a.total ?? a.F)) as any[]
    : []);
  const en = (n: unknown) => (typeof n === 'number' ? n.toLocaleString('sv-SE', { maximumFractionDigits: 1 }) : '–');
</script>

{#if !kvarter}
  <header class="topp">
    <span class="skede">Parti {id}</span>
    <h1>Vilket kvarter är ni?</h1>
  </header>
  {#if saknas}
    <p class="panel">Partiet finns inte. Kontrollera koden eller <a href="#/">starta ett nytt</a>.</p>
  {:else if forhand}
    <div class="panel val">
      {#each forhand.kvarter.filter(k => k.styrning === 'människa') as k}
        <a class="kvarterknapp" href="#/parti/{id}/{encodeURIComponent(k.namn)}">{k.namn}</a>
      {/each}
      <a class="kvarterknapp bordet" href="#/parti/{id}/bordet">
        {forhand.slump === 'inmatad' ? 'Bordet (tärningar och kort)' : 'Bara titta'}
      </a>
      <p class="dela">Dela länken med de andra: <code>{lank}</code>
        <button type="button" onclick={kopiera}>{kopierat ? 'Kopierad' : 'Kopiera'}</button></p>
    </div>
  {:else}
    <p class="panel">Hämtar partiet …</p>
  {/if}
{:else}
  <header class="rad">
    <div>
      <span class="skede">Parti {id} · {kvarter === 'bordet' ? 'Bordet' : kvarter}</span>
      <h1>{lage?.bild?.namn ?? 'ÅKEPOL'}</h1>
    </div>
    <span class="status status-{anslutning?.status}">{anslutning?.status === 'ansluten' ? 'Ansluten' : anslutning?.status === 'ansluter' ? 'Ansluter …' : 'Förbindelsen bruten, försöker igen'}</span>
  </header>

  {#if anslutning?.raderat}
    <p class="panel">Partiet har raderats. <a href="#/">Till startsidan</a></p>
  {:else if lage?.fel}
    <p class="panel fel" role="alert">Partiet stannade: {lage.fel}</p>
  {:else if lage?.klart}
    <section class="panel">
      <h2>Slutställning</h2>
      <div class="tabell">
        <table>
          <thead><tr><th>Kvarter</th><th>PU</th><th>TG</th><th>F</th><th>Mu</th><th>Totalt</th></tr></thead>
          <tbody>
            {#each resultat as r, i}
              <tr class:vinnare={i === 0}><td>{i === 0 ? '🏆 ' : ''}{r.spelare}</td><td>{en(r.PU)}</td><td>{en(r.TG)}</td><td>{en(r.F)}</td><td>{en(r.Mu)}</td><td><strong>{en(r.total ?? r.F)}</strong></td></tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="not">Slutpoäng = (PU + TG + F) × Mu. <a href="#/">Nytt parti</a></p>
    </section>
  {:else}
  {#if lage?.ledare}<Spelledare ledare={lage.ledare} jag={kvarter} />{/if}
  <div class="spelyta" class:med-brade={visaBrade}>
  <div class="huvud">
  {#if fraga && minTur}
    <Fraga {fraga} svara={s => anslutning?.svara(fraga.nr, s)} skickar={anslutning?.skickar} />
  {:else if fraga}
    <p class="panel vantar">
      {#if fraga.kanal === 'slump'}Väntar på bordet: {fraga.vy.rubrik}
      {:else}Väntar på <strong>{fraga.kvarter}</strong> ({skedenamn[fraga.skede ?? ''] ?? ''}): {fraga.vy.rubrik}{/if}
    </p>
  {:else}
    <p class="panel">Ansluter till partiet …</p>
  {/if}
  {#if lage?.slump === 'digital'}
    <Bordet visningar={lage.bordet ?? []} />
  {/if}
  </div>
  {#if visaBrade && lage?.bild}
    <Brade kvarter={lage.bild.kvarter as any} jag={kvarter} aktiv={fraga?.kvarter ?? null} bank={lage.bild.projektbank?.length ?? 0} />
  {/if}
  </div>
  {/if}
  {#if anslutning?.fel}<p class="panel fel" role="alert">{anslutning.fel}</p>{/if}

  {#if lage}
    <Lage bild={lage.bild} jag={kvarter} svar={lage.svar} slump={lage.drag ?? []} />
  {/if}
{/if}

<style>
  .topp { padding-block: 20px 14px; border-bottom: 3px solid var(--pu); margin-bottom: 18px; display: grid; gap: 4px; }
  .rad { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: end; gap: 8px; padding-block: 16px 12px; border-bottom: 3px solid var(--pu); margin-bottom: 14px; }
  .skede { font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--pu-mork); }
  h1 { margin: 0; font-size: clamp(24px, 4.5vw, 34px); }
  h2 { margin: 0 0 8px; }
  .spelyta { display: grid; gap: 12px; align-items: start; }
  .spelyta.med-brade { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  @media (max-width: 820px) { .spelyta.med-brade { grid-template-columns: minmax(0, 1fr); } }
  .huvud { min-width: 0; }
  .panel { background: var(--panel); border-radius: 6px; padding: 14px 16px; margin: 0 0 12px; }
  .val { display: grid; gap: 8px; max-width: 520px; }
  .kvarterknapp { display: block; padding: 14px 16px; border-radius: 6px; background: var(--black); color: var(--panel); font-weight: 700; font-size: 18px; text-decoration: none; }
  .kvarterknapp:hover { background: var(--pu-mork); }
  .kvarterknapp.bordet { background: #fff; color: var(--black); border: 1px solid var(--black); }
  .dela { margin: 6px 0 0; font-size: 13.5px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .dela code { word-break: break-all; }
  .dela button { font: inherit; padding: 4px 10px; border-radius: 4px; border: 1px solid var(--black); background: #fff; cursor: pointer; }
  .status { font-size: 13px; font-weight: 700; padding: 3px 8px; border-radius: 3px; background: var(--panel); }
  .status-ansluten { color: var(--ok); }
  .status-borta { color: var(--fel); }
  .vantar { font-size: 16px; }
  .fel { color: var(--fel); font-weight: 700; }
  .tabell { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
  th, td { padding: 6px 10px; text-align: right; border-bottom: 1px solid var(--panel-mork); }
  th:first-child, td:first-child { text-align: left; }
  .vinnare td { font-weight: 700; }
  .not { margin: 10px 0 0; font-size: 14px; color: var(--dampad); }
  a { color: var(--black); }
  a:focus-visible, button:focus-visible { outline: 3px solid var(--pu); outline-offset: 2px; }
</style>
