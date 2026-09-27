<script lang="ts">
  // Förvaltningen (Skede 3): spiralen på brädet med var ni är, era fastigheter med korten och
  // brickorna på dem, er hand, marknaden och de andras fastigheter (bara det som ligger synligt).
  import data from '../data/pussel.json';
  import Kort from './Kort.svelte';
  import type { Bild } from './anslutning.svelte';

  let { bild, jag }: { bild: Bild; jag: string } = $props();

  const fargar = data.fargar as Record<string, { fyllning: string; ljus: string }>;
  const tal = (n: unknown) => (typeof n === 'number' ? n.toLocaleString('sv-SE', { maximumFractionDigits: 1 }) : '–');

  // ---------------------------------------------------------------- spiralen
  // Brädets stationer medsols från toppen; varv 1 (kvartal 1) är det yttersta, spiralen går inåt mot Resultat.
  const STATIONER = [
    ['marknad', 'Marknad', -90], ['omvarld', 'Omvärld', -30], ['ekonomi', 'Ekonomi', 30],
    ['fastigheter', 'Fastigheter', 90], ['omgivning', 'Omgivning', 150], ['energi', 'Energi', 210],
  ] as const;
  const radie = (q: number) => 118 - (q - 1) * 22;
  const punkt = (q: number, grad: number) => {
    const v = (grad * Math.PI) / 180;
    return [160 + radie(q) * Math.cos(v), 160 + radie(q) * Math.sin(v)];
  };
  const nuIndex = $derived(STATIONER.findIndex(s => s[0] === bild.fas));
  const q = $derived(bild.kvartal ?? 0);
  const passerad = (kv: number, i: number) => kv < q || (kv === q && i < nuIndex);

  // yieldbanan (9.10): ändringen på platserna Q2–Q4, öppet för alla; yielden flyttas i början av kvartalet
  const SPAR = [['bostäder', 'Bostäder'], ['kommersiellt', 'Kommersiellt']] as const;
  const andring = (v: number) => (v > 0 ? `+${tal(v)}` : v < 0 ? `−${tal(-v)}` : '±0');

  const egen = $derived(bild.kvarter.find(k => k.namn === jag));
  const andra = $derived(bild.kvarter.filter(k => k.namn !== jag));
  const brickor = (f: any) => [
    f.dn_brickor ? `Dolt driftnetto ${f.dn_brickor > 0 ? '+' : ''}${f.dn_brickor}` : '',
    f.ek_brickor ? `Dold energi ${f.ek_brickor > 0 ? '+' : ''}${f.ek_brickor}` : '',
    f.plus_att_visa ? `${f.plus_att_visa} plusbricka att visa` : '',
  ].filter(Boolean);
</script>

<section class="forvaltning" aria-label="Förvaltningen">
  <figure class="spiral">
    <svg viewBox="0 0 320 320" role="img"
         aria-label={q ? `Kvartal ${q}, ${STATIONER[nuIndex]?.[1] ?? ''}` : 'Innan första kvartalet'}>
      {#each [1, 2, 3, 4] as kv}
        <circle cx="160" cy="160" r={radie(kv)} class="varv" class:aktivt={kv === q} />
        {#each STATIONER as [id, , grad], i}
          {@const [x, y] = punkt(kv, grad)}
          <circle cx={x} cy={y} r={kv === q && i === nuIndex ? 9 : 5.5}
                  class="station" class:passerad={passerad(kv, i)} class:nu={kv === q && i === nuIndex}>
            <title>Kvartal {kv}: {STATIONER[i][1]}</title>
          </circle>
        {/each}
        {@const [tx, ty] = punkt(kv, 250)}
        <text x={tx} y={ty + 4} class="varvtal">{kv}</text>
      {/each}
      <text x="160" y="164" class="mitt">Resultat</text>
      {#each STATIONER as [id, namn, grad]}
        {@const v = (grad * Math.PI) / 180}
        <text x={160 + 146 * Math.cos(v)} y={160 + 146 * Math.sin(v) + 4} class="etikett" class:nu={id === bild.fas}>{namn}</text>
      {/each}
    </svg>
    {#if bild.yieldbana}
      <table class="yieldbana">
        <caption>Yieldbanan</caption>
        <thead><tr><th>Spår</th><th>Start</th><th>Q2</th><th>Q3</th><th>Q4</th><th>Nu</th></tr></thead>
        <tbody>
          {#each SPAR as [id, namn]}
            <tr>
              <th scope="row">{namn}</th>
              <td>{tal(bild.startyield?.[id])} %</td>
              {#each bild.yieldbana[id] ?? [] as v, i}
                <td class:gjord={q >= i + 2} class:nasta={q === i + 1}>{andring(v)}</td>
              {/each}
              <td class="nu">{tal(bild.yield?.[id])} %</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
    <figcaption>{q ? `Kvartal ${q} av 4` : 'Innan första kvartalet'}{nuIndex >= 0 ? ` · ${STATIONER[nuIndex][1]}` : ''}
      </figcaption>
  </figure>

  {#if egen}
    <div class="egen">
      <h3>Ert kvarter · kassa {tal(egen.kassa)} Mkr · riskbuffert {egen.riskbuffert}</h3>
      {#if egen.start}
        <p class="personal">Startkassa {tal(egen.start.kassa)} Mkr = {[`TB ${tal(egen.start.tb)}`,
          ...(egen.start.brf ?? []).map((b: any) => `${b.namn} såld ${tal(b.intakt)}`),
          ...(egen.start.lan ? [`moderbolagslån ${egen.start.lan} × 95`] : [])].join(' + ')}</p>
      {/if}
      <p class="personal">FC {egen.fc ?? '–'}{egen.fc_senior ? ' (senior)' : ''} · FS {egen.fs ?? '–'}{egen.fs_senior ? ' (senior)' : ''}
        {#if egen.vantande_kassa}· {tal(egen.vantande_kassa)} Mkr väntar till nästa marknad{/if}</p>
      <div class="fastigheter">
        {#each egen.fastigheter as f, i (i)}
          <article class="fastighet" style="--typ:{fargar[f.typkod]?.fyllning ?? '#888'};--ljus:{fargar[f.typkod]?.ljus ?? '#fff'}">
            <header><span>{f.typ}</span><span class="ek">{f.ek}</span></header>
            <h4>{f.namn}</h4>
            <dl>
              <div><dt>Driftnetto</dt><dd>{tal(f.dn)} Mkr/år</dd></div>
              <div><dt>Marknadsvärde</dt><dd>{tal(f.mv)} Mkr</dd></div>
              <div><dt>Lån</dt><dd>{tal(f.lan)} Mkr</dd></div>
            </dl>
            {#if brickor(f).length || f.varningar || f.villkor?.length}
              <ul class="brickor">
                {#each brickor(f) as b}<li>{b}</li>{/each}
                {#if f.varningar}<li class="varning">⚠ {f.varningar} underhållsvarning{f.varningar > 1 ? 'ar' : ''} {f.varningar >= 3 ? '– driftnettot −1 tills de tas bort med kort' : ''}</li>{/if}
                {#each f.villkor as v}<li class="villkor">Villkor: {v.replace(/^villkor:\s*/i, '')}</li>{/each}
              </ul>
            {/if}
          </article>
        {:else}
          <p class="tom">Inga fastigheter just nu.</p>
        {/each}
      </div>

      {#if egen.handkort?.length}
        <h3>Er hand · {egen.handkort.length} kort</h3>
        <div class="rad">
          {#each egen.handkort as k, i (i)}<Kort kort={k} lek="nätverk" skede="F" />{/each}
        </div>
      {/if}
    </div>
  {/if}

  {#if bild.marknad?.length}
    <div class="marknad">
      <h3>På marknaden</h3>
      <ul>
        {#each bild.marknad as f}
          <li><span class="prick" style="background:{fargar[f.typkod]?.fyllning ?? '#888'}"></span>{f.namn} · DN {tal(f.dn)} · MV {tal(f.mv)} · lån {tal(f.lan)} · {f.ek}</li>
        {/each}
      </ul>
    </div>
  {/if}

  {#each andra as k (k.namn)}
    <div class="annan">
      <h3>{k.namn} · kassa {tal(k.kassa)} Mkr · riskbuffert {k.riskbuffert} · {k.hand} kort på hand</h3>
      <ul>
        {#each k.fastigheter as f, i (i)}
          <li><span class="prick" style="background:{fargar[f.typkod]?.fyllning ?? '#888'}"></span>{f.namn} · DN {tal(f.dn)} · MV {tal(f.mv)} · {f.ek}
            {#if f.varningar} · ⚠ {f.varningar}{/if}{#each f.villkor as v} · villkor: {v.replace(/^villkor:\s*/i, '')}{/each}</li>
        {:else}<li>Inga fastigheter.</li>{/each}
      </ul>
    </div>
  {/each}
</section>

<style>
  .forvaltning { display: grid; gap: 12px; }
  .spiral { margin: 0; background: var(--panel); border-radius: 6px; padding: 10px; display: grid; justify-items: center; gap: 4px; }
  .spiral svg { width: min(100%, 320px); height: auto; }
  .spiral figcaption { font-weight: 700; text-align: center; font-size: 14px; }
  .yieldbana { border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
  .yieldbana caption { font-weight: 700; padding-bottom: 4px; }
  .yieldbana th, .yieldbana td { padding: 3px 7px; text-align: center; border-bottom: 1px solid var(--panel-mork); }
  .yieldbana th[scope="row"] { text-align: left; }
  .yieldbana .gjord { color: var(--dampad); text-decoration: line-through; }
  .yieldbana .nasta { font-weight: 700; background: #f0c7c2; }
  .yieldbana .nu { font-weight: 700; }
  .varv { fill: none; stroke: #f0c7c2; stroke-width: 10; }
  .varv.aktivt { stroke: #ef9c93; }
  .station { fill: #fff; stroke: #c9776d; stroke-width: 2; }
  .station.passerad { fill: #c9776d; }
  .station.nu { fill: #ef5656; stroke: #7a2020; stroke-width: 3; }
  .varvtal { font: 700 11px var(--typsnitt); fill: #7a2020; text-anchor: middle; }
  .mitt { font: 700 13px var(--typsnitt); fill: #7a2020; text-anchor: middle; }
  .etikett { font: 600 11.5px var(--typsnitt); fill: var(--dampad); text-anchor: middle; }
  .etikett.nu { fill: #7a2020; font-weight: 700; }

  .egen, .marknad, .annan { background: var(--panel); border-radius: 6px; padding: 12px; display: grid; gap: 8px; }
  h3 { margin: 0; font-size: 15px; }
  .personal { margin: 0; color: var(--dampad); font-size: 14px; }
  .fastigheter { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
  .fastighet { background: var(--ljus); border-radius: 8px; overflow: hidden; box-shadow: 0 2px 6px rgba(0, 0, 0, .15); }
  .fastighet header { background: var(--typ); color: #fff; display: flex; justify-content: space-between; padding: 4px 8px;
                      font-size: 11.5px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
  .ek { background: #fff; color: var(--black); border-radius: 3px; padding: 0 5px; }
  .fastighet h4 { margin: 6px 8px 0; font-size: 15px; }
  .fastighet dl { margin: 4px 8px; display: grid; gap: 1px; font-size: 13px; }
  .fastighet dl div { display: flex; justify-content: space-between; gap: 6px; }
  .fastighet dt { color: var(--dampad); }
  .fastighet dd { margin: 0; font-weight: 700; font-variant-numeric: tabular-nums; }
  .brickor { list-style: none; margin: 0 8px 8px; padding: 0; display: grid; gap: 3px; font-size: 12.5px; }
  .brickor li { background: rgba(255, 255, 255, .7); border-radius: 3px; padding: 2px 6px; }
  .brickor .varning { color: var(--fel); font-weight: 700; }
  .rad { display: flex; gap: 10px; overflow-x: auto; padding: 2px 2px 8px; }
  .marknad ul, .annan ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 3px; font-size: 14px; }
  .prick { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
  .tom { margin: 0; color: var(--dampad); }
</style>
