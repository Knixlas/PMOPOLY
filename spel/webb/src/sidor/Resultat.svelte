<script lang="ts">
  // Bara resultat: ni spelar hela spelet på brädet och för in slutsiffrorna per kvarter. Appen räknar
  // PU, TG, F, Mu och slutpoängen (regelboken kapitel 10) och visar placeringen. Siffrorna sparas i
  // den här webbläsaren, så sidan kan laddas om.
  import { poang, T_KRAV, type Siffror } from '../spel/poang';

  let { namn }: { namn: string[] } = $props();

  const nyckel = () => `akepol-resultat-${namn.join(',')}`;   // sidan skapas om när namnen ändras (App: #key)
  const tom = (): Record<keyof Siffror, number | null> => ({
    abt: null, qKrav: null, hKrav: null, tPaverkan: 0, tb: null, q: null, h: null, t: T_KRAV,
    egetKapital: null, kassa: null, lan: 0,
  });
  function las(): Record<string, Record<keyof Siffror, number | null>> {
    try {
      const sparat = JSON.parse(localStorage.getItem(nyckel()) ?? 'null');
      if (sparat) return sparat;
    } catch { /* ingen lagring: börja tomt */ }
    return Object.fromEntries(namn.map(n => [n, tom()]));
  }
  let data = $state(las());
  $effect(() => {
    const json = JSON.stringify(data);
    try { localStorage.setItem(nyckel(), json); } catch { /* sparas inte, sidan fungerar ändå */ }
  });

  const komplett = (d: Record<keyof Siffror, number | null>) => Object.values(d).every(v => typeof v === 'number' && !Number.isNaN(v));
  const resultat = $derived(namn.map(n => ({ namn: n, klar: komplett(data[n]), p: komplett(data[n]) ? poang(data[n] as Siffror) : null })));
  const topplista = $derived(resultat.filter(r => r.p).sort((a, b) => b.p!.total - a.p!.total));
  const tal = (v: number) => v.toLocaleString('sv-SE', { maximumFractionDigits: 1 });

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
</script>

<header class="topp">
  <span class="skede">ÅKEPOL · Bara resultat</span>
  <h1>Slutpoäng</h1>
  <p>För in varje kvarters siffror när ni spelat klart på brädet. Poängen räknas medan ni skriver.</p>
</header>

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
                <input type="number" inputmode="decimal" step="any" bind:value={data[r.namn][nyckel]} />
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

<p class="not"><a href="#/">Till startsidan</a></p>

<style>
  .topp { padding-block: 20px 14px; border-bottom: 3px solid var(--pu); margin-bottom: 18px; display: grid; gap: 4px; }
  .skede { font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--pu-mork); }
  h1 { margin: 0; font-size: clamp(28px, 5vw, 40px); }
  .topp p { margin: 0; max-width: 60ch; }
  .panel { background: var(--panel); border-radius: 6px; padding: 16px; display: grid; gap: 12px; margin-bottom: 14px; }
  h2 { margin: 0; font-size: 20px; }
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
