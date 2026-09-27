<script lang="ts">
  // Spelläget: varje kvarters siffror i det skede partiet är i. Det egna kvarteret först.
  import type { Bild } from './anslutning.svelte';
  import Forvaltning from './Forvaltning.svelte';
  import Handen from './Handen.svelte';

  let { bild, jag, svar = [], slump = [] }: {
    bild: Bild | null; jag: string; svar?: { kvarter: string; rubrik: string; svar: string }[]; slump?: string[];
  } = $props();
  const kvarter = $derived(bild ? [...bild.kvarter].sort((a, b) => (a.namn === jag ? -1 : b.namn === jag ? 1 : 0)) : []);
  const tal = (n: unknown) => (typeof n === 'number' ? n.toLocaleString('sv-SE', { maximumFractionDigits: 1 }) : '–');
  const procent = (n: number) => n.toLocaleString('sv-SE', { maximumFractionDigits: 1 }) + ' %';   // yielden lagras i procent
</script>

<section class="lage" aria-label="Spelläget">
  {#if !bild}
    <p class="tom">Partiet startar …</p>
  {:else}
    <header>
      <span class="skede skede-{bild.skede}">{bild.namn}</span>
      {#if bild.skede === 'F' && bild.kvartal}<span>Kvartal {bild.kvartal}</span>{/if}
      {#if bild.yield}<span>Yield bostäder {procent(bild.yield['bostäder'] ?? 0)} · kommersiellt {procent(bild.yield['kommersiellt'] ?? 0)}</span>{/if}
    </header>

    {#if bild.skede === 'S2'}
      {@const egen = bild.kvarter.find(k => k.namn === jag)}
      {#if egen}<Handen fasKort={bild.fas_kort ?? null} kvarter={egen} />{/if}
    {/if}

    {#if bild.skede === 'F'}
      <Forvaltning {bild} {jag} />
    {:else}
    <div class="kort">
      {#each kvarter as k (k.namn)}
        <article class:jag={k.namn === jag}>
          <h3>{k.namn}{k.namn === jag ? ' (ni)' : ''}</h3>
          {#if bild.skede === 'PU'}
            <dl>
              <div><dt>Projekt</dt><dd>{k.antal ?? k.projekt?.length ?? 0}</dd></div>
              <div><dt>BTA</dt><dd>{tal(k.bta)} kvm</dd></div>
              <div><dt>Anskaffning</dt><dd>{tal(k.anskaffning)} Mkr</dd></div>
              <div><dt>Marknadsvärde</dt><dd>{tal(k.marknadsvarde)} Mkr</dd></div>
              <div title="Tomten + markexpansioner + projektens utvecklingskostnad (5.1)"><dt>ABT-kostnad</dt><dd>{tal(k.abt_kostnad)} Mkr</dd></div>
              <div title="Anskaffning minus ABT-kostnad: vad kvarteret har att bygga för i Skede 2"><dt>ABT-budget nu</dt><dd>{tal(k.abt)} Mkr</dd></div>
              <div><dt>Q-krav</dt><dd>{k.q_krav}</dd></div>
              <div><dt>H-krav</dt><dd>{k.h_krav}</dd></div>
              <div><dt>Nämndsumma</dt><dd>{k.namndsumma}</dd></div>
              <div><dt>Riskbuffert</dt><dd>{k.riskbuffert}</dd></div>
              <div><dt>Mark</dt><dd>{k.mark} rutor</dd></div>
              <div><dt>Ruta · varv</dt><dd>{k.ruta?.toLowerCase()} · {k.varv}</dd></div>
            </dl>
            {#if k.projekt?.length}<p class="lista">{k.projekt.map((p: any) => p.namn).join(' · ')}</p>{/if}
          {:else if bild.skede === 'S2'}
            <dl>
              <div><dt>Q</dt><dd>{k.q} / {k.q_krav}</dd></div>
              <div><dt>H</dt><dd>{k.h} / {k.h_krav}</dd></div>
              <div><dt>T</dt><dd>{k.t}</dd></div>
              <div><dt>Kvar av ABT</dt><dd>{tal(k.kvar)} Mkr</dd></div>
              <div><dt>Riskbuffert</dt><dd>{k.riskbuffert}</dd></div>
              <div><dt>Erfarenhet</dt><dd>{k.erfarenhet}</dd></div>
            </dl>
          {:else if bild.skede === 'F'}
            <dl>
              <div><dt>Kassa</dt><dd>{tal(k.kassa)} Mkr</dd></div>
              <div><dt>Riskbuffert</dt><dd>{k.riskbuffert}</dd></div>
              <div><dt>Handkort</dt><dd>{k.hand}</dd></div>
              <div><dt>Fastigheter</dt><dd>{k.fastigheter?.length ?? 0}</dd></div>
            </dl>
            {#if k.fastigheter?.length}
              <table>
                <thead><tr><th>Fastighet</th><th>DN</th><th>MV</th><th>Lån</th><th>EK</th></tr></thead>
                <tbody>
                  {#each k.fastigheter as f}
                    <tr><td>{f.namn}{f.varningar ? ` ⚠${f.varningar}` : ''}</td><td>{tal(f.dn)}</td><td>{tal(f.mv)}</td><td>{tal(f.lan)}</td><td>{f.ek}</td></tr>
                  {/each}
                </tbody>
              </table>
            {/if}
          {/if}
        </article>
      {/each}
    </div>

    {/if}

    {#if slump.length}
      <details class="logg" open>
        <summary>Tärningar och kort</summary>
        <ol reversed>
          {#each [...slump].reverse().slice(0, 8) as t}
            <li class:tarning={t.startsWith('Tärning')}>{t}</li>
          {/each}
        </ol>
      </details>
    {/if}
    {#if bild.handelser?.length || svar.length}
      <details class="logg" open>
        <summary>Senaste händelserna</summary>
        <ol reversed>
          {#each [...svar].reverse().slice(0, 8) as s}
            <li><strong>{s.kvarter}:</strong> {s.rubrik} — {s.svar}</li>
          {/each}
          {#each [...bild.handelser].reverse().slice(0, 12) as h}
            <li class="motor">{h}</li>
          {/each}
        </ol>
      </details>
    {/if}
  {/if}
</section>

<style>
  .lage { display: grid; gap: 12px; }
  .tom { margin: 0; }
  header { display: flex; flex-wrap: wrap; gap: 6px 14px; align-items: baseline; font-size: 14px; }
  .skede { font-weight: 700; font-size: 13px; letter-spacing: .1em; text-transform: uppercase; padding: 3px 8px; border-radius: 3px; background: var(--black); color: var(--panel); }
  .skede-PU { background: #dda063; color: var(--black); }
  .skede-S2 { background: #1a6b9a; }
  .skede-F { background: #ef5656; }
  .kort { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 10px; }
  article { background: var(--panel); border-radius: 6px; padding: 10px 12px; display: grid; gap: 8px; align-content: start; border: 2px solid transparent; min-width: 0; }
  article.jag { border-color: var(--black); }
  h3 { margin: 0; font-size: 16px; }
  dl { margin: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
  dt { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--dampad); }
  dd { margin: 0; font-weight: 700; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
  .lista { margin: 0; font-size: 13px; color: var(--dampad); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; display: block; overflow-x: auto; }
  th, td { text-align: right; padding: 2px 6px; border-bottom: 1px solid var(--panel-mork); }
  th:first-child, td:first-child { text-align: left; }
  .logg { background: var(--panel); border-radius: 6px; padding: 8px 12px; font-size: 13.5px; }
  .logg summary { cursor: pointer; font-weight: 700; }
  .logg ol { margin: 6px 0 0; padding-left: 18px; display: grid; gap: 3px; max-height: 240px; overflow: auto; }
  .motor { color: var(--dampad); }
  .tarning { font-weight: 700; font-variant-numeric: tabular-nums; }
</style>
