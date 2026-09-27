<script lang="ts">
  // Ett kort som spelarna ser det: lekens färg överst, rubrik, text och (för projekt) bilden.
  import data from '../data/pussel.json';
  import type { Kortvy } from './anslutning.svelte';

  let { kort, lek = '', skede = null, kvarter = null, ny = false, stor = false }: {
    kort: Kortvy; lek?: string; skede?: string | null; kvarter?: string | null; ny?: boolean; stor?: boolean;
  } = $props();

  const fargar = data.fargar as Record<string, { fyllning: string; ljus: string }>;
  const SKEDEFARG = { PU: '#DDA063', PL: '#1A6B9A', G: '#91B542', F: '#EF5656' };
  const G_LEKAR = /^(FAS|kultur|konsekvens|garanti)/;
  const farg = $derived.by(() => {
    if (kort.bild && fargar[kort.typ]) return fargar[kort.typ].fyllning;
    if (skede === 'G' || G_LEKAR.test(lek)) return SKEDEFARG.G;
    if (skede === 'S2') return SKEDEFARG.PL;
    if (skede === 'F' || /^(händelse|handelse|kvartal|dd|natverk|omvarld|yield)/.test(lek)) return SKEDEFARG.F;
    return SKEDEFARG.PU;
  });
  const leknamn = (l: string) => l.replace(/_/g, ' ').replace(/^handelse/, 'händelse').replace(/^natverk$/, 'nätverk')
    .replace(/^omvarld$/, 'omvärld').replace(/^dd$/, 'DD');
</script>

<article class="kort" class:ny class:stor style="--farg:{farg}">
  <header><span>{leknamn(lek)}</span><span class="id">{kort.id}</span></header>
  {#if kort.bild}<img src={kort.bild} alt="" />{/if}
  <h3>{kort.rubrik}</h3>
  {#if kort.text}<p>{kort.text}</p>{/if}
  {#if kort.rader?.length}
    <dl>{#each kort.rader as [k, t]}<div><dt>{k}</dt><dd>{t}</dd></div>{/each}</dl>
  {/if}
  {#if kvarter}<footer>{kvarter}</footer>{/if}
</article>

<style>
  .kort { flex: none; width: 168px; min-height: 200px; background: var(--panel); border-radius: 8px; overflow: hidden;
          display: grid; align-content: start; box-shadow: 0 5px 10px rgba(0, 0, 0, .3); color: var(--black); }
  .kort.stor { width: min(100%, 260px); min-height: 0; box-shadow: 0 3px 8px rgba(0, 0, 0, .2); border: 1px solid var(--panel-mork); }
  .stor h3 { font-size: 17px; }
  .stor p { font-size: 14px; -webkit-line-clamp: 10; line-clamp: 10; }
  header { background: var(--farg); color: #fff; display: flex; justify-content: space-between; gap: 6px;
           padding: 5px 8px; font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
  .id { opacity: .85; }
  img { width: 90px; height: 78px; object-fit: cover; margin: 8px auto 0; display: block;
        clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%); }
  h3 { margin: 8px 8px 0; font-size: 14.5px; line-height: 1.2; text-wrap: balance; }
  p { margin: 4px 8px 0; font-size: 12.5px; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 6;
      line-clamp: 6; -webkit-box-orient: vertical; overflow: hidden; }
  dl { margin: 6px 8px 0; display: grid; gap: 1px; font-size: 11.5px; }
  dl div { display: flex; justify-content: space-between; gap: 6px; border-top: 1px solid var(--panel-mork); padding-top: 1px; }
  dt { color: var(--dampad); white-space: nowrap; }
  dd { margin: 0; text-align: right; font-weight: 700; }
  footer { margin: 8px; font-size: 11.5px; color: var(--dampad); }
  article > :last-child { margin-bottom: 8px; }

  @media (prefers-reduced-motion: no-preference) {
    .kort.ny { animation: vand .6s cubic-bezier(.2, .7, .3, 1) both; transform-origin: center; backface-visibility: hidden; }
  }
  @keyframes vand {
    0% { transform: translateY(-30px) rotateY(180deg) scale(.85); opacity: 0; }
    60% { opacity: 1; }
    100% { transform: none; opacity: 1; }
  }
</style>
