<script lang="ts">
  // Spelledaren: var partiet är (skede, steg, plats), vad ni gör vid bordet nu, och – om ni vill –
  // regelbokens avsnitt för steget. Valet att visa reglerna sparas på enheten.
  import regler from '../data/regler.json';
  import type { Ledare } from './anslutning.svelte';

  let { ledare, jag }: { ledare: Ledare; jag: string } = $props();

  const avsnitt = regler as Record<string, { rubrik: string; html: string }>;
  const NYCKEL = 'akepol-visa-regler';
  let visaRegler = $state(false);
  try { visaRegler = localStorage.getItem(NYCKEL) === 'ja'; } catch { /* privat läge */ }
  function vaxla() {
    visaRegler = !visaRegler;
    try { localStorage.setItem(NYCKEL, visaRegler ? 'ja' : 'nej'); } catch { /* ingen lagring */ }
  }

  const nu = $derived(ledare.steg.findIndex(s => s.id === ledare.nu));
</script>

<section class="ledare" aria-label="Spelledaren">
  <div class="topp">
    <div>
      <p class="skede">{ledare.skede}</p>
      <p class="plats">
        {ledare.steg[nu]?.namn}{ledare.plats ? ` · ${ledare.plats}` : ''}
        {#if ledare.tur}<span class="tur">{ledare.tur === jag ? 'Er tur' : `${ledare.tur}s tur`}</span>{/if}
      </p>
    </div>
    <button type="button" class="regelknapp" aria-pressed={visaRegler} onclick={vaxla}>
      {visaRegler ? 'Dölj reglerna' : 'Visa reglerna'}
    </button>
  </div>

  <ol class="steg" aria-label="Skedets steg">
    {#each ledare.steg as s, i (s.id)}
      <li class:nu={i === nu} class:klar={i < nu} aria-current={i === nu ? 'step' : undefined}>{s.namn}</li>
    {/each}
  </ol>

  <p class="gor"><strong>Nu:</strong> {ledare.gor}</p>

  {#if visaRegler}
    <div class="regler">
      {#each ledare.regler.filter(id => avsnitt[id]) as id, i (id)}
        <details open={i === 0}>
          <summary>{avsnitt[id].rubrik}</summary>
          <div class="text">{@html avsnitt[id].html}</div>
        </details>
      {/each}
    </div>
  {/if}
</section>

<style>
  .ledare { background: var(--black); color: var(--panel); border-radius: 6px; padding: 12px 14px; margin: 0 0 12px;
            display: grid; gap: 8px; }
  .topp { display: flex; justify-content: space-between; align-items: start; gap: 10px; }
  .skede { margin: 0; font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: var(--pu); font-weight: 700; }
  .plats { margin: 2px 0 0; font-size: 19px; font-weight: 700; line-height: 1.2; }
  .tur { margin-left: 8px; font-size: 13px; padding: 2px 7px; border-radius: 3px; background: var(--pu); color: var(--black); vertical-align: 2px; }
  .regelknapp { flex: none; font: inherit; font-weight: 700; font-size: 13.5px; padding: 6px 10px; border-radius: 4px;
                border: 1px solid var(--panel); background: transparent; color: var(--panel); cursor: pointer; }
  .regelknapp[aria-pressed='true'] { background: var(--panel); color: var(--black); }
  .regelknapp:focus-visible { outline: 3px solid var(--pu); outline-offset: 2px; }
  .steg { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 4px; counter-reset: steg; }
  .steg li { counter-increment: steg; font-size: 13px; padding: 3px 8px; border-radius: 3px;
             background: rgba(252, 246, 239, .12); color: rgba(252, 246, 239, .6); }
  .steg li::before { content: counter(steg) ". "; }
  .steg li.klar { color: var(--panel); }
  .steg li.nu { background: var(--pu); color: var(--black); font-weight: 700; }
  .gor { margin: 0; font-size: 15px; max-width: 72ch; }
  .regler { display: grid; gap: 6px; background: var(--panel); color: var(--black); border-radius: 4px; padding: 8px 12px; }
  .regler summary { cursor: pointer; font-weight: 700; }
  .text { font-size: 14.5px; line-height: 1.5; max-width: 72ch; overflow-x: auto; }
  .text :global(table) { border-collapse: collapse; font-size: 13.5px; margin: 6px 0; }
  .text :global(th), .text :global(td) { border: 1px solid var(--panel-mork); padding: 3px 6px; text-align: left; }
  .text :global(aside) { background: var(--panel-mork); border-radius: 4px; padding: 6px 10px; margin: 6px 0; }
  .text :global(p) { margin: 6px 0; }
  .text :global(ul) { padding-left: 20px; }
</style>
