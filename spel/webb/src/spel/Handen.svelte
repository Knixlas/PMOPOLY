<script lang="ts">
  // Skede 2: fasens kort (Genomförandet) och ert kvarters hand – kompetenskorten ni kan spela.
  // Nivåerna visas för er kvartertyp, med en bock där handens kompetens räcker.
  import Kort from './Kort.svelte';
  import type { Kortvy } from './anslutning.svelte';

  let { fasKort = null, kvarter }: { fasKort?: Kortvy | null; kvarter: Record<string, any> } = $props();

  const KOMP: Record<string, string> = { STA: 'Stabilitet', KOM: 'Kommunikation', SAM: 'Samarbete', NOG: 'Noggrannhet', INN: 'Innovation', ABM: 'Arbetsmiljö' };
  function racker(krav: string): boolean {
    const har = kvarter.kompetens ?? {};
    return [...krav.matchAll(/([A-Z]{3}) (\d+)/g)].every(([, k, n]) => (har[k] ?? 0) >= Number(n));
  }
</script>

<section class="handen" aria-label="Fasen och handen">
  {#if fasKort}
    <div class="fas">
      <Kort kort={fasKort} lek={fasKort.lek ?? 'FAS'} skede="G" stor />
      {#if kvarter.fas_krav?.length}
        <table>
          <caption>Nivåerna för ert kvarter</caption>
          <thead><tr><th>Nivå</th><th>Krav</th><th>Effekt</th><th><span class="sr">Räcker handen?</span></th></tr></thead>
          <tbody>
            {#each kvarter.fas_krav as [niva, krav, effekt]}
              {@const ok = krav === '—' || racker(krav)}
              <tr class:ok><td>{niva}</td><td>{krav === '—' ? 'inget' : krav}</td><td>{effekt || 'ingen effekt'}</td>
                <td>{ok ? '✓' : ''}</td></tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  {/if}

  {#if kvarter.handkort?.length}
    <h3>Er hand · {kvarter.handkort.length} kort</h3>
    {#if Object.keys(kvarter.kompetens ?? {}).length}
      <p class="summa">Tillsammans: {Object.entries(kvarter.kompetens).map(([k, n]) => `${KOMP[k] ?? k} ${n}`).join(' · ')}</p>
    {/if}
    <div class="rad">
      {#each kvarter.handkort as k, i (i)}
        <Kort kort={k} lek={k.typ || 'kompetens'} skede="S2" />
      {/each}
    </div>
  {/if}
</section>

<style>
  .handen { background: var(--panel); border-radius: 6px; padding: 12px; display: grid; gap: 10px; }
  .fas { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-start; }
  table { border-collapse: collapse; font-size: 14px; font-variant-numeric: tabular-nums; flex: 1 1 260px; }
  caption { text-align: left; font-weight: 700; padding-bottom: 4px; }
  th, td { text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--panel-mork); vertical-align: top; }
  tr.ok td:last-child { color: var(--ok); font-weight: 700; }
  h3 { margin: 0; font-size: 13px; letter-spacing: .1em; text-transform: uppercase; }
  .summa { margin: 0; font-size: 14px; color: var(--dampad); }
  .rad { display: flex; gap: 10px; overflow-x: auto; padding: 2px 2px 8px; }
  .sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
