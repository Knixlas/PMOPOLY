<script lang="ts">
  // Bara resultat: ni spelar hela spelet på brädet och för in slutsiffrorna per kvarter. Appen räknar
  // PU, TG, F, Mu och slutpoängen (regelboken kapitel 10) och visar placeringen. Siffrorna sparas på
  // servern, så flera kan fylla i från sina mobiler och resultatet finns kvar.
  import { onDestroy } from 'svelte';
  import { hamtaResultat, sparaResultat, type ResultatData, type Siffror as SiffrorData } from '../spel/anslutning.svelte';
  import { poang, T_KRAV, type Siffror } from '../spel/poang';

  let { id }: { id: string } = $props();

  let res = $state<ResultatData | null>(null);
  let fel = $state('');
  let status = $state<'sparat' | 'sparar' | 'andrat' | 'fel'>('sparat');
  let andrade = new Set<string>();                       // kvarter med ändringar som inte skickats än
  let timer: ReturnType<typeof setTimeout> | undefined;

  async function hamta() {
    try {
      const ny = await hamtaResultat(id);
      if (!res) { res = ny; return; }
      // andras ändringar tas in, men inte över det vi själva håller på att skriva
      for (const n of ny.kvarter) if (!andrade.has(n)) res.siffror[n] = ny.siffror[n];
    } catch (e) { if (!res) fel = (e as Error).message; }
  }
  $effect(() => { void id; hamta(); });
  const poll = setInterval(() => { if (status === 'sparat') hamta(); }, 5000);
  onDestroy(() => { clearInterval(poll); clearTimeout(timer); });

  function andra(namn: string) {
    andrade.add(namn);
    status = 'andrat';
    clearTimeout(timer);
    timer = setTimeout(spara, 700);
  }
  async function spara() {
    if (!res) return;
    const skicka: Record<string, SiffrorData> = {};
    for (const n of andrade) skicka[n] = $state.snapshot(res.siffror[n]) as SiffrorData;
    andrade = new Set();
    status = 'sparar';
    try { await sparaResultat(id, skicka); status = andrade.size ? 'andrat' : 'sparat'; }
    catch { for (const n of Object.keys(skicka)) andrade.add(n); status = 'fel'; }
  }

  const komplett = (d: SiffrorData) => Object.values(d).every(v => typeof v === 'number' && !Number.isNaN(v));
  const resultat = $derived((res?.kvarter ?? []).map(n => {
    const d = res!.siffror[n];
    return { namn: n, p: komplett(d) ? poang(d as unknown as Siffror) : null };
  }));
  const topplista = $derived(resultat.filter(r => r.p).sort((a, b) => b.p!.total - a.p!.total));
  const tal = (v: number) => v.toLocaleString('sv-SE', { maximumFractionDigits: 1 });
  const statustext = { sparat: 'Sparat', sparar: 'Sparar …', andrat: 'Ändrat', fel: 'Kunde inte spara – försöker igen när du ändrar' };

  const FALT: { skede: string; falt: [keyof Siffror, string, string?][] }[] = [
    { skede: 'Skede 1 · Projektutveckling', falt: [
      ['abt', 'ABT-budget (Mkr)', 'Anskaffning − PU-kostnad'], ['qKrav', 'Q-krav'], ['hKrav', 'H-krav'],
      ['tPaverkan', 'T-påverkan', 'Projektens tidspåverkan (0 om ingen)']] },
    { skede: 'Skede 2 · Genomförande', falt: [
      ['tb', 'Täckningsbidrag (Mkr)', 'ABT-budget − ABT-kostnad'], ['q', 'Q-utfall'], ['h', 'H-utfall'],
      ['t', 'T-utfall (månader)', `Krav ${T_KRAV}`]] },
    { skede: 'Förvaltning', falt: [
      ['egetKapital', 'Eget kapital (Mkr)', 'Summa marknadsvärde − lån, på yielden efter Q4'], ['kassa', 'Kassa (Mkr)', 'Restkort räknas som kassa'],
      ['lan', 'Moderbolagslån (antal)']] },
  ];
  const lank = $derived(`${location.origin}${location.pathname}#/resultat/${id}`);
</script>

<header class="topp">
  <span class="skede">ÅKEPOL · Bara resultat · {id}</span>
  <h1>Slutpoäng</h1>
  <p>För in varje kvarters siffror när ni spelat klart på brädet. Poängen räknas medan ni skriver och sparas på
    servern – flera kan fylla i samtidigt med länken <code>{lank}</code>.</p>
</header>

{#if fel}
  <p class="panel fel" role="alert">Resultatet gick inte att hämta: {fel}. <a href="#/">Till startsidan</a></p>
{:else if !res}
  <p class="panel">Hämtar …</p>
{:else}
  <p class="status status-{status}" aria-live="polite">{statustext[status]}</p>

  {#if topplista.length}
    <section class="panel">
      <h2>Placering</h2>
      <div class="tabell">
        <table>
          <thead><tr><th>Kvarter</th><th>PU</th><th>TG</th><th>F</th><th>Mu</th><th>Totalt</th></tr></thead>
          <tbody>
            {#each topplista as r, i}
              <tr class:vinnare={i === 0}><td>{i === 0 ? '🏆 ' : ''}{r.namn}</td><td>{tal(r.p!.pu)}</td><td>{tal(r.p!.tg)}</td>
                <td>{tal(r.p!.f)}</td><td>{Math.round(r.p!.mu * 100)} %</td><td><strong>{tal(r.p!.total)}</strong></td></tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="not">Slutpoäng = (PU + TG + F) × Mu. PU = ABT ÷ (Q-krav + H-krav + T-påverkan) · TG = TB ÷ ABT i procent ·
        F = (eget kapital + halva kassan − 100 per moderbolagslån) ÷ 30 · Mu efter antal avvikelser (10.2).</p>
    </section>
  {/if}

  <div class="kvarter">
    {#each resultat as r (r.namn)}
      <section class="panel">
        <h2>{r.namn}</h2>
        {#each FALT as grupp}
          <fieldset>
            <legend>{grupp.skede}</legend>
            <div class="falt">
              {#each grupp.falt as [nyckel, etikett, hjalp]}
                <label>
                  <span>{etikett}</span>
                  <input type="number" inputmode="decimal" step="any" bind:value={res.siffror[r.namn][nyckel]}
                         oninput={() => andra(r.namn)} />
                  {#if hjalp}<small>{hjalp}</small>{/if}
                </label>
              {/each}
            </div>
          </fieldset>
        {/each}
        {#if r.p}
          <p class="summa">PU {tal(r.p.pu)} · TG {tal(r.p.tg)} % · F {tal(r.p.f)} · {r.p.avvikelser} avvikelser → Mu {Math.round(r.p.mu * 100)} %
            · <strong>{tal(r.p.total)} poäng</strong></p>
        {:else}
          <p class="summa tom">Fyll i alla fält för att få poängen.</p>
        {/if}
      </section>
    {/each}
  </div>
{/if}

<p class="not"><a href="#/">Till startsidan</a></p>

<style>
  .topp { padding-block: 20px 14px; border-bottom: 3px solid var(--pu); margin-bottom: 18px; display: grid; gap: 4px; }
  .skede { font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--pu-mork); }
  h1 { margin: 0; font-size: clamp(28px, 5vw, 40px); }
  .topp p { margin: 0; max-width: 60ch; }
  .topp code { overflow-wrap: anywhere; font-size: 13px; }
  .panel { background: var(--panel); border-radius: 6px; padding: 16px; display: grid; gap: 12px; margin-bottom: 14px; }
  .fel { color: var(--fel); }
  h2 { margin: 0; font-size: 20px; }
  .status { margin: 0 0 10px; font-size: 13px; font-weight: 700; color: var(--dampad); }
  .status-sparat { color: var(--ok); }
  .status-fel { color: var(--fel); }
  .kvarter { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 14px; }
  fieldset { border: none; padding: 0; margin: 0; display: grid; gap: 6px; }
  legend { font-weight: 700; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 4px; }
  .falt { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  label { display: grid; gap: 2px; font-size: 14px; align-content: start; }
  input { font: inherit; font-weight: 700; padding: 7px 9px; border: 1px solid var(--linje-stark); border-radius: 4px;
          background: #fff; color: var(--black); min-width: 0; font-variant-numeric: tabular-nums; }
  small { color: var(--dampad); font-size: 12px; }
  .summa { margin: 0; padding: 8px 10px; background: #fff; border-radius: 4px; font-variant-numeric: tabular-nums; }
  .summa.tom { color: var(--dampad); }
  .tabell { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--panel-mork); }
  tr.vinnare td { font-weight: 700; }
  .not { margin: 0; color: var(--dampad); font-size: 14px; }
</style>
