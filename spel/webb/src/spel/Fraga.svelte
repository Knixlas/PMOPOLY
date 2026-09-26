<script lang="ts">
  // Den aktuella frågan och sättet att svara på den. Varje frågetyp har sitt eget svarsläge;
  // "Gör som förslaget" finns alltid (bottens val), så att ingen fråga kan fastna.
  import data from '../data/pussel.json';
  import Pussel from '../pussel/Pussel.svelte';
  import { cellerFor, lagdFran, type Del, type Lagd } from '../pussel/kvarter';
  import { type Form, type Ruta } from '../pussel/regler';
  import type { Fraga, Svar } from './anslutning.svelte';

  let { fraga, svara, skickar = false }: { fraga: Fraga; svara: (s: Svar) => void; skickar?: boolean } = $props();
  const vy = $derived(fraga.vy);
  const fargar = data.fargar as Record<string, { fyllning: string; ljus: string }>;

  let valda = $state<number[]>([]);
  let tal = $state(0);
  let sok = $state('');
  $effect.pre(() => {
    void fraga.nr;
    valda = [...(vy.valda ?? [])];
    sok = '';
    tal = vy.typ === 'tal' ? (vy.min ?? 0) : 0;
  });

  const synliga = $derived((vy.alternativ ?? []).map((a, i) => ({ ...a, i }))
    .filter(a => !sok || (a.text + ' ' + (a.detalj ?? '')).toLowerCase().includes(sok.toLowerCase())));

  // ------------------------------------------------------------------ pusslet (4.3 och markexpansion)
  const projektData = new Map(data.projekt.map(p => [p.namn, p]));
  // Lagd mark: varje markexpansion är en egen bit som får flyttas (kant i kant med marken).
  function lagdMark(): { delar: Del[]; start: Lagd[] } {
    const delar: Del[] = [], start: Lagd[] = [];
    for (const b of vy.markbitar ?? []) {
      const form = b.form as Form;
      delar.push({ id: b.id, namn: b.id, typ: 'MARK', form, bya: form.length * 250 });
      start.push({ id: b.id, lager: 0, ...lagdFran(form, b.celler as Ruta[]) });
    }
    return { delar, start };
  }

  const pussel = $derived.by(() => {
    if (vy.typ !== 'pussel' && vy.typ !== 'markexpansion') return null;
    const { delar, start } = lagdMark();
    if (vy.typ === 'pussel') {
      for (const p of vy.projekt ?? []) {
        const d = projektData.get(p.namn);
        delar.push({ id: p.namn, namn: p.namn, typ: p.typ, form: p.form as Form, bta: d?.bta, bild: d?.bild });
      }
    } else {
      delar.push({ id: vy.id!, namn: 'Ny markexpansion', typ: 'MARK', form: vy.form as Form, bya: (vy.form?.length ?? 0) * 250 });
    }
    return { delar, start, delMap: new Map(delar.map(d => [d.id, d])) };
  });

  function lamnaPussel(lagda: Lagd[]) {
    if (!pussel) return;
    const cell = (l: Lagd) => { const d = pussel.delMap.get(l.id)!; return cellerFor(d.form, l.lage, l.rad, l.kol); };
    const arMark = (l: Lagd) => pussel.delMap.get(l.id)!.typ === 'MARK';
    const mark = lagda.filter(arMark).map(l => [l.id, cell(l)]);
    if (vy.typ === 'pussel') {
      const placering = lagda.filter(l => !arMark(l)).map(l => [l.id, cell(l), l.lager]);
      svara({ placering, mark });
      return;
    }
    if (lagda.some(l => l.id === vy.id)) svara({ mark });
  }
  const kravMarkexpansion = (lagda: Lagd[]) => (lagda.some(l => l.id === vy.id) ? null : 'Lägg markexpansionen på tomten först.');
</script>

<section class="fraga" aria-live="polite">
  <h2>{vy.rubrik}</h2>
  {#if vy.hjalp}<p class="hjalp">{vy.hjalp}</p>{/if}

  {#if vy.typ === 'janej'}
    <div class="knappar">
      <button type="button" class="stor" disabled={skickar} onclick={() => svara({ svar: true })}>Ja</button>
      <button type="button" class="stor" disabled={skickar} onclick={() => svara({ svar: false })}>Nej</button>
    </div>
  {:else if vy.typ === 'tal'}
    {#if (vy.max ?? 0) - (vy.min ?? 0) <= 20}
      <div class="rutnat" role="group" aria-label="Välj ett tal">
        {#each Array((vy.max ?? 0) - (vy.min ?? 0) + 1) as _, i}
          <button type="button" class="tal" disabled={skickar} onclick={() => svara({ svar: (vy.min ?? 0) + i })}>{(vy.min ?? 0) + i}</button>
        {/each}
      </div>
    {:else}
      <div class="knappar">
        <label for="tal-{fraga.nr}">Tal ({vy.min}–{vy.max})</label>
        <input id="tal-{fraga.nr}" type="number" min={vy.min} max={vy.max} bind:value={tal} />
        <button type="button" class="stor" disabled={skickar} onclick={() => svara({ svar: Math.round(tal) })}>Svara</button>
      </div>
    {/if}
  {:else if vy.typ === 'val' || vy.typ === 'flerval'}
    {#if (vy.alternativ?.length ?? 0) > 8}
      <input class="sok" type="search" placeholder="Sök kort eller namn" bind:value={sok} aria-label="Sök bland alternativen" />
    {/if}
    <ul class="alternativ">
      {#each synliga as a (a.i)}
        <li>
          {#if vy.typ === 'val'}
            <button type="button" class="alt" class:medbild={!!a.bild} disabled={skickar} onclick={() => svara({ val: a.i })}
                    style={a.typ ? `--typ:${fargar[a.typ]?.fyllning ?? 'transparent'}` : ''}>
              {#if a.bild}<img src={a.bild} alt="" loading="lazy" />{/if}
              <span class="text">{a.text}</span>{#if a.detalj}<span class="detalj">{a.detalj}</span>{/if}
            </button>
          {:else}
            <label class="alt kryss">
              <input type="checkbox" checked={valda.includes(a.i)}
                     disabled={!valda.includes(a.i) && vy.max !== undefined && valda.length >= vy.max}
                     onchange={e => (valda = (e.currentTarget as HTMLInputElement).checked ? [...valda, a.i] : valda.filter(x => x !== a.i))} />
              <span class="text">{a.text}</span>{#if a.detalj}<span class="detalj">{a.detalj}</span>{/if}
            </label>
          {/if}
        </li>
      {/each}
    </ul>
    {#if vy.typ === 'flerval'}
      <div class="knappar">
        <button type="button" class="stor" disabled={skickar} onclick={() => svara({ flera: valda })}>
          {valda.length ? `Klart (${valda.length} valda)` : 'Inga, gå vidare'}
        </button>
      </div>
    {/if}
  {:else if pussel}
    <Pussel delar={pussel.delar} start={pussel.start} fargar={data.fargar} lamnaIn={lamnaPussel} lamnaText={vy.typ === 'pussel' ? 'Lämna in kvarteret' : 'Lägg markexpansionen här'}
            lamnaKrav={vy.typ === 'markexpansion' ? kravMarkexpansion : undefined} />
  {/if}

  {#if fraga.kanal === 'beslut' && vy.forslag_text !== undefined}
    <p class="forslag">
      Förslag: <strong>{vy.forslag_text}</strong>
      <button type="button" class="lank" disabled={skickar} onclick={() => svara({ forslag: true })}>Gör som förslaget</button>
    </p>
  {/if}
</section>

<style>
  .fraga { background: var(--panel); border-radius: 6px; padding: 16px; display: grid; gap: 12px; }
  h2 { margin: 0; font-size: 22px; line-height: 1.2; text-wrap: balance; }
  .hjalp { margin: -4px 0 0; color: var(--dampad); font-size: 14.5px; }
  .knappar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  button { font: inherit; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
  .stor { font-weight: 700; font-size: 17px; padding: 10px 22px; border-radius: 4px; border: 1px solid var(--black);
          background: var(--black); color: var(--panel); min-width: 96px; }
  .stor:hover:not(:disabled) { background: var(--pu-mork); border-color: var(--pu-mork); }
  .rutnat { display: grid; grid-template-columns: repeat(auto-fill, minmax(46px, 1fr)); gap: 6px; max-width: 520px; }
  .tal { font-weight: 700; font-size: 17px; padding: 10px 0; border-radius: 4px; border: 1px solid var(--linje-stark);
         background: #fff; color: var(--black); font-variant-numeric: tabular-nums; }
  .tal:hover:not(:disabled) { background: var(--pu); }
  .sok { font: inherit; padding: 8px 10px; border: 1px solid var(--linje-stark); border-radius: 4px; max-width: 360px; }
  .alternativ { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; max-height: 60vh; overflow: auto; }
  .alt { width: 100%; display: grid; gap: 2px; text-align: left; padding: 9px 12px; border-radius: 4px;
         border: 1px solid var(--linje-stark); background: #fff; color: var(--black); }
  .alt:hover:not(:disabled) { border-color: var(--black); background: var(--panel-mork); }
  .kryss { grid-template-columns: auto 1fr; column-gap: 10px; cursor: pointer; }
  .medbild { grid-template-columns: 52px 1fr; column-gap: 12px; align-items: center; border-left: 6px solid var(--typ); }
  .medbild img { grid-row: span 2; width: 52px; height: 45px; object-fit: cover;
                 clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%); }
  .kryss .detalj { grid-column: 2; }
  .text { font-weight: 700; font-size: 15.5px; }
  .detalj { font-size: 13px; color: var(--dampad); }
  .forslag { margin: 0; font-size: 14px; color: var(--dampad); display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: baseline; }
  .lank { background: none; border: none; padding: 0; color: var(--pu-mork); font-weight: 700; text-decoration: underline; }
  button:focus-visible, input:focus-visible, label:focus-within { outline: 3px solid var(--pu); outline-offset: 2px; }
  input[type='number'] { font: inherit; width: 90px; padding: 8px; border-radius: 4px; border: 1px solid var(--linje-stark); }
</style>
