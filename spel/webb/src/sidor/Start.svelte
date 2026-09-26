<script lang="ts">
  // Starta ett parti (1–4 kvarter, människor eller bottar, digitalt eller vid brädet) eller gå med i ett.
  import { listaPartier, skapaParti } from '../spel/anslutning.svelte';

  const forslag = ['Norr', 'Söder', 'Öster', 'Väster'];
  let kvarter = $state([{ namn: 'Norr', styrning: 'människa' }, { namn: 'Söder', styrning: 'människa' }]);
  let slump = $state<'digital' | 'inmatad'>('digital');
  let fel = $state('');
  let skapar = $state(false);
  let partier = $state<Awaited<ReturnType<typeof listaPartier>>>([]);
  let kod = $state('');

  $effect(() => { listaPartier().then(p => (partier = p)).catch(() => {}); });

  function laggTill() {
    if (kvarter.length >= 4) return;
    const namn = forslag.find(n => !kvarter.some(k => k.namn === n)) ?? `Kvarter ${kvarter.length + 1}`;
    kvarter = [...kvarter, { namn, styrning: 'bott' }];
  }

  async function skapa(e: SubmitEvent) {
    e.preventDefault();
    fel = '';
    const namn = kvarter.map(k => k.namn.trim());
    if (namn.some(n => !n) || new Set(namn).size !== namn.length) { fel = 'Ge kvarteren olika namn.'; return; }
    skapar = true;
    try {
      const id = await skapaParti({ kvarter: kvarter.map(k => ({ ...k, namn: k.namn.trim() })), slump });
      location.hash = `#/parti/${id}`;
    } catch (err) {
      fel = `Partiet gick inte att skapa: ${(err as Error).message}`;
    } finally {
      skapar = false;
    }
  }
</script>

<header class="topp">
  <span class="skede">ÅKEPOL · Husbyggspelet</span>
  <h1>Nytt parti</h1>
  <p>Varje kvarter spelar på sin egen mobil eller surfplatta. Starta partiet här och dela länken.</p>
</header>

<div class="spalter">
  <form class="panel" onsubmit={skapa}>
    <h2>Kvarteren</h2>
    <ul class="kvarter">
      {#each kvarter as k, i}
        <li>
          <label for="kv-{i}" class="dold">Kvarter {i + 1}</label>
          <input id="kv-{i}" bind:value={k.namn} maxlength="30" autocomplete="off" />
          <select id="styr-{i}" bind:value={k.styrning} aria-label="Vem spelar {k.namn}">
            <option value="människa">Spelare</option>
            <option value="bott">Datorn</option>
          </select>
          {#if kvarter.length > 1}
            <button type="button" class="ta-bort" aria-label="Ta bort {k.namn}" onclick={() => (kvarter = kvarter.filter((_, j) => j !== i))}>×</button>
          {/if}
        </li>
      {/each}
    </ul>
    {#if kvarter.length < 4}<button type="button" class="sekundar" onclick={laggTill}>Lägg till kvarter</button>{/if}

    <fieldset>
      <legend>Hur spelar ni?</legend>
      <label class="val"><input type="radio" name="slump" value="digital" bind:group={slump} />
        <span><strong>Helt i appen</strong><br />Appen slår tärningarna och drar korten.</span></label>
      <label class="val"><input type="radio" name="slump" value="inmatad" bind:group={slump} />
        <span><strong>Vid brädet</strong><br />Ni spelar med det fysiska spelet och anger tärningar och dragna kort. Appen håller ordning på regler och poäng.</span></label>
    </fieldset>

    {#if fel}<p class="fel" role="alert">{fel}</p>{/if}
    <button type="submit" class="primar" disabled={skapar}>{skapar ? 'Startar …' : 'Starta partiet'}</button>
  </form>

  <section class="panel">
    <h2>Gå med i ett parti</h2>
    <form class="rad" onsubmit={e => { e.preventDefault(); if (kod.trim()) location.hash = `#/parti/${kod.trim()}`; }}>
      <label for="kod" class="dold">Partiets kod</label>
      <input id="kod" bind:value={kod} placeholder="Partiets kod" autocomplete="off" />
      <button type="submit" class="sekundar">Gå med</button>
    </form>
    {#if partier.length}
      <h3>Partier på servern</h3>
      <ul class="partier">
        {#each partier.slice(0, 12) as p}
          <li><a href="#/parti/{p.id}"><strong>{p.kvarter.join(', ')}</strong>
            <span>{p.klart ? 'Klart' : p.skede ?? ''} · {p.slump === 'inmatad' ? 'vid brädet' : 'i appen'} · {p.id}</span></a></li>
        {/each}
      </ul>
    {/if}
    <p class="lank"><a href="#/pussel">Prova kvarterspusslet</a></p>
  </section>
</div>

<style>
  .topp { padding-block: 20px 14px; border-bottom: 3px solid var(--pu); margin-bottom: 18px; display: grid; gap: 4px; }
  .skede { font-size: 12px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--pu-mork); }
  h1 { margin: 0; font-size: clamp(28px, 5vw, 40px); }
  .topp p { margin: 0; max-width: 60ch; }
  .spalter { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 18px; align-items: start; }
  @media (max-width: 760px) { .spalter { grid-template-columns: minmax(0, 1fr); } }
  .panel { background: var(--panel); border-radius: 6px; padding: 16px; display: grid; gap: 12px; }
  h2 { margin: 0; font-size: 20px; }
  h3 { margin: 4px 0 0; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; }
  .kvarter { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
  .kvarter li { display: flex; gap: 8px; align-items: center; }
  input, select { font: inherit; padding: 8px 10px; border: 1px solid var(--linje-stark); border-radius: 4px; background: #fff; color: var(--black); min-width: 0; }
  .kvarter input { flex: 1; font-weight: 700; }
  .ta-bort { font: inherit; font-size: 20px; line-height: 1; width: 36px; height: 36px; border-radius: 4px; border: 1px solid var(--linje-stark); background: #fff; cursor: pointer; }
  fieldset { border: none; padding: 0; margin: 0; display: grid; gap: 8px; }
  legend { font-weight: 700; margin-bottom: 6px; }
  .val { display: flex; gap: 10px; align-items: flex-start; padding: 10px; border: 1px solid var(--linje-stark); border-radius: 4px; background: #fff; cursor: pointer; font-size: 14.5px; }
  .val input { margin-top: 3px; }
  .val:has(input:checked) { border-color: var(--black); box-shadow: inset 0 0 0 1px var(--black); }
  .primar { font: inherit; font-weight: 700; font-size: 17px; padding: 12px 18px; border-radius: 4px; border: none; background: var(--pu); color: var(--black); cursor: pointer; }
  .primar:hover:not(:disabled) { background: var(--pu-mork); color: #fff; }
  .sekundar { font: inherit; font-weight: 600; padding: 8px 14px; border-radius: 4px; border: 1px solid var(--black); background: #fff; color: var(--black); cursor: pointer; justify-self: start; }
  .rad { display: flex; gap: 8px; }
  .rad input { flex: 1; }
  .partier { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  .partier a { display: grid; gap: 2px; padding: 8px 10px; border-radius: 4px; background: #fff; color: var(--black); text-decoration: none; border: 1px solid transparent; }
  .partier a:hover { border-color: var(--black); }
  .partier span { font-size: 13px; color: var(--dampad); }
  .fel { margin: 0; color: var(--fel); font-weight: 700; }
  .lank { margin: 0; }
  .lank a { color: var(--black); font-weight: 700; }
  .dold { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  button:focus-visible, input:focus-visible, select:focus-visible, a:focus-visible { outline: 3px solid var(--pu); outline-offset: 2px; }
</style>
