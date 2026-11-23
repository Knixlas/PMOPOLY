<script lang="ts">
  // Placeringspusslet: tomten, handen och allt man gör med bitarna.
  // Dra en bit till tomten, eller tryck på den så lyfts den upp över marken. Medan man håller en
  // bit: R eller hjulet vrider, F eller högerklick speglar, pilarna flyttar, Enter lägger, Esc släpper.
  import Minibit from './Minibit.svelte';
  import { cellerFor, forstaPlats, kanLyfta, lagdFran, orienterad, prova, somBitar, type Del, type Lagd } from './kvarter';
  import { losa } from './losare';
  import { BOSTAD, TOMT, granska, lagen, nyckel, spegla, vridMedurs, type Form, type Ruta } from './regler';

  let { delar, start = [], fargar, lasta = [], lamnaIn, lamnaText = 'Lämna in', lamnaKrav }: {
    delar: Del[];
    start?: Lagd[];
    fargar: Record<string, { fyllning: string; ljus: string }>;
    lasta?: string[];                               // bitar som ligger fast (t.ex. mark som redan är lagd)
    lamnaIn?: (lagda: Lagd[]) => void;              // i spelet: lämna in kvarteret
    lamnaText?: string;
    lamnaKrav?: (lagda: Lagd[]) => string | null;   // skäl att inte kunna lämna in än (null = går)
  } = $props();

  const S = 40;                                   // rutans storlek i SVG-enheter
  const delMap = $derived(new Map(delar.map(d => [d.id, d])));

  let lagda = $state<Lagd[]>([]);
  let historik = $state<Lagd[][]>([]);
  let framtid = $state<Lagd[][]>([]);
  let meddelande = $state('');
  let raknar = $state(false);
  $effect.pre(() => { lagda = start.map(l => ({ ...l })); historik = []; framtid = []; meddelande = ''; });

  interface Grepp {
    id: string;
    lage: number;
    rad: number;
    kol: number;
    index: number;              // vilken av formens rutor man håller i
    fran: Lagd | null;          // var den låg innan (null = från handen)
    lyfter: boolean;            // pekaren är nere (drar) — annars svävar biten och väntar
    overBrade: boolean;
    x: number; y: number;       // pekarens position på skärmen
    startX: number; startY: number; startTid: number;
  }
  let grepp = $state<Grepp | null>(null);
  let svg = $state<SVGSVGElement>();
  let skarmRuta = $state(24);                      // en rutas storlek på skärmen, för draget utanför tomten

  const ovriga = $derived(grepp ? lagda.filter(l => l.id !== grepp!.id) : lagda);
  const bitar = $derived(somBitar(ovriga, delMap));
  const g = $derived(granska(bitar));
  const markRutor = $derived([...g.mark].map(n => [Math.floor(n / TOMT), n % TOMT] as Ruta));
  const grundmark = new Set<number>();
  for (let r = 6; r < 10; r++) for (let k = 6; k < 10; k++) grundmark.add(nyckel(r, k));

  // Vyn: tomten beskuren runt marken (plus plats för markexpansionerna), så att rutorna blir stora
  // på mobilen. Ramen står still medan man drar, annars skulle rutorna flytta sig under fingret.
  // plats runt marken för markexpansionerna i handen (och den man håller)
  const marginal = $derived(Math.max(1, ...delar.filter(d => d.typ === 'MARK' && (iHanden.includes(d) || grepp?.id === d.id))
    .flatMap(d => d.form).map(([r, k]) => Math.max(r, k) + 1)));
  function berakna(): { r0: number; k0: number; n: number } {
    const alla = [...granska(somBitar(lagda, delMap)).mark].map(x => [Math.floor(x / TOMT), x % TOMT]);
    const rr = alla.map(c => c[0]), kk = alla.map(c => c[1]);
    let r0 = Math.min(...rr) - marginal, r1 = Math.max(...rr) + marginal;
    let k0 = Math.min(...kk) - marginal, k1 = Math.max(...kk) + marginal;
    const n = Math.min(TOMT, Math.max(8, r1 - r0 + 1, k1 - k0 + 1));
    r0 = Math.max(0, Math.min(TOMT - n, Math.round((r0 + r1 + 1 - n) / 2)));
    k0 = Math.max(0, Math.min(TOMT - n, Math.round((k0 + k1 + 1 - n) / 2)));
    return { r0, k0, n };
  }
  let ram = $state({ r0: 0, k0: 0, n: TOMT });
  $effect(() => { if (!grepp?.lyfter) ram = berakna(); });

  const hallen = $derived(grepp ? delMap.get(grepp.id)! : null);
  const skugga = $derived(grepp && hallen ? cellerFor(hallen.form, grepp.lage, grepp.rad, grepp.kol) : []);
  const prov = $derived(grepp && hallen && grepp.overBrade ? prova(hallen, skugga, ovriga, delMap) : null);

  let doljUppe = $state(false);                   // visa bara markplanet (lager 1)
  const uppeRutor = $derived(new Set(somBitar(ovriga.filter(l => l.lager === 2), delMap)
    .flatMap(b => b.celler.map(([r, k]) => nyckel(r, k)))));
  const finnsUppe = $derived(lagda.some(l => l.lager === 2));

  const iHanden = $derived(delar.filter(d => !lagda.some(l => l.id === d.id)));
  const projekt = $derived(delar.filter(d => d.typ !== 'MARK'));
  const lagdaProjekt = $derived(lagda.filter(l => delMap.get(l.id)!.typ !== 'MARK'));
  const bya = $derived(somBitar(lagdaProjekt.filter(l => l.lager === 1), delMap).reduce((s, b) => s + b.celler.length, 0) * 250);
  const bta = $derived(lagdaProjekt.reduce((s, l) => s + (delMap.get(l.id)!.bta ?? 0), 0));

  const farg = (typ: string) => fargar[typ]?.fyllning ?? '#888';
  const typnamn: Record<string, string> = { MARK: 'Markexpansion', BRF: 'BRF', HYRESRÄTT: 'Hyresrätt', FÖRSKOLA: 'Förskola', LOKAL: 'Lokal', KONTOR: 'Kontor' };
  const tal = (n: number) => n.toLocaleString('sv-SE');
  /** Bitens ytterkant som SVG-väg: de rutkanter som inte gränsar mot en egen ruta. */
  function kontur(celler: Ruta[]): string {
    const egna = new Set(celler.map(([r, k]) => nyckel(r, k)));
    const har = (r: number, k: number) => r >= 0 && k >= 0 && r < TOMT && k < TOMT && egna.has(nyckel(r, k));
    let d = '';
    for (const [r, k] of celler) {
      const x = k * S, y = r * S;
      if (!har(r - 1, k)) d += `M${x} ${y}h${S}`;
      if (!har(r + 1, k)) d += `M${x} ${y + S}h${S}`;
      if (!har(r, k - 1)) d += `M${x} ${y}v${S}`;
      if (!har(r, k + 1)) d += `M${x + S} ${y}v${S}`;
    }
    return d;
  }
  const bokstav: Record<string, string> = { BRF: 'B', HYRESRÄTT: 'H', FÖRSKOLA: 'F', LOKAL: 'L', KONTOR: 'K', MARK: '' };

  // ------------------------------------------------------------------ historik
  function spara(nytt: Lagd[]) {
    historik = [...historik, lagda.map(l => ({ ...l }))];
    framtid = [];
    lagda = nytt;
  }
  function angra() {
    if (!historik.length) return;
    framtid = [...framtid, lagda];
    lagda = historik[historik.length - 1];
    historik = historik.slice(0, -1);
    grepp = null;
  }
  function gorOm() {
    if (!framtid.length) return;
    historik = [...historik, lagda];
    lagda = framtid[framtid.length - 1];
    framtid = framtid.slice(0, -1);
    grepp = null;
  }

  // ------------------------------------------------------------------ pekaren
  function rutaUnder(x: number, y: number): Ruta | null {
    if (!svg) return null;
    const ctm = svg.getScreenCTM();
    if (!ctm) return null;
    const p = new DOMPoint(x, y).matrixTransform(ctm.inverse());
    const r = Math.floor(p.y / S), k = Math.floor(p.x / S);
    return r >= 0 && r < TOMT && k >= 0 && k < TOMT ? [r, k] : null;
  }

  function flyttaTill(gr: Grepp, cell: Ruta) {
    const o = orienterad(delMap.get(gr.id)!.form, gr.lage)[gr.index];
    gr.rad = cell[0] - o[0];
    gr.kol = cell[1] - o[1];
  }

  function mattSkarm() {
    if (svg) skarmRuta = svg.getBoundingClientRect().width / ram.n;
  }

  function lyftUrHanden(e: PointerEvent, d: Del) {
    if (e.button !== 0) return;
    e.preventDefault();
    mattSkarm();
    meddelande = '';
    const mitt = Math.floor(d.form.length / 2);
    grepp = { id: d.id, lage: 0, rad: 6, kol: 6, index: mitt, fran: null, lyfter: true, overBrade: false,
      x: e.clientX, y: e.clientY, startX: e.clientX, startY: e.clientY, startTid: performance.now() };
    lyssna();
  }

  function lyftFranTomten(e: PointerEvent, l: Lagd, index: number) {
    if (e.button !== 0 || grepp) return;
    e.preventDefault();
    e.stopPropagation();
    if (lasta.includes(l.id)) { meddelande = 'Den här marken är redan lagd och ligger fast.'; return; }
    const hinder = kanLyfta(l.id, lagda, delMap);
    if (hinder) { meddelande = hinder; return; }
    mattSkarm();
    meddelande = '';
    grepp = { id: l.id, lage: l.lage, rad: l.rad, kol: l.kol, index, fran: { ...l }, lyfter: true, overBrade: true,
      x: e.clientX, y: e.clientY, startX: e.clientX, startY: e.clientY, startTid: performance.now() };
    lyssna();
  }

  function greppaSkuggan(e: PointerEvent, index: number) {
    if (!grepp || e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    grepp.index = index;
    grepp.lyfter = true;
    grepp.startX = e.clientX; grepp.startY = e.clientY; grepp.startTid = performance.now();
    lyssna();
  }

  function tryckPaTomten(e: PointerEvent) {
    // svävar en bit: tryck på tomten flyttar dit den
    if (!grepp || grepp.lyfter || e.button !== 0) return;
    const cell = rutaUnder(e.clientX, e.clientY);
    if (cell) { flyttaTill(grepp, cell); grepp.overBrade = true; }
  }

  function lyssna() {
    window.addEventListener('pointermove', rorelse);
    window.addEventListener('pointerup', slapp);
    window.addEventListener('pointercancel', slapp);
  }
  function sluta() {
    window.removeEventListener('pointermove', rorelse);
    window.removeEventListener('pointerup', slapp);
    window.removeEventListener('pointercancel', slapp);
  }

  function rorelse(e: PointerEvent) {
    if (!grepp?.lyfter) return;
    grepp.x = e.clientX;
    grepp.y = e.clientY;
    const cell = rutaUnder(e.clientX, e.clientY);
    grepp.overBrade = cell !== null;
    if (cell) flyttaTill(grepp, cell);
  }

  function slapp(e: PointerEvent) {
    sluta();
    if (!grepp) return;
    const tryck = Math.hypot(e.clientX - grepp.startX, e.clientY - grepp.startY) < 6 && performance.now() - grepp.startTid < 350;
    grepp.lyfter = false;
    if (tryck) {                                   // ett tryck: lyft upp biten så den svävar
      if (!grepp.fran) svava(grepp);
      meddelande = 'Vrid och spegla med knapparna överst. Flytta genom att dra biten eller trycka på tomten. Tryck Lägg när den är grön.';
      return;
    }
    if (!grepp.overBrade) { tillbaka(); return; }
    if (prov && prov.lager !== null) lagg();
    else meddelande = prov?.skal ?? '';
  }

  /** Lägg biten svävande på första stället där den får ligga (eller mitt på marken). */
  function svava(gr: Grepp) {
    const d = delMap.get(gr.id)!;
    const plats = forstaPlats(d, lagda.filter(l => l.id !== gr.id), delMap);
    gr.overBrade = true;
    if (plats) { gr.lage = plats.lage; gr.rad = plats.rad; gr.kol = plats.kol; }
    else flyttaTill(gr, [7, 7]);
    visaTomten();
  }
  /** På mobilen ligger handen ovanför tomten: rulla så att tomten syns när man tagit upp en bit. */
  function visaTomten() {
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    if (r.top < 60 || r.bottom > innerHeight) svg.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
  function valjMedTangent(d: Del) {
    mattSkarm();
    const gr: Grepp = { id: d.id, lage: 0, rad: 6, kol: 6, index: 0, fran: null, lyfter: false, overBrade: true, x: 0, y: 0, startX: 0, startY: 0, startTid: 0 };
    svava(gr);
    grepp = gr;
  }

  // ------------------------------------------------------------------ handlingar med biten man håller
  function vrid() {
    if (!grepp) return;
    const d = delMap.get(grepp.id)!;
    const fore = orienterad(d.form, grepp.lage)[grepp.index];
    const halls: Ruta = [grepp.rad + fore[0], grepp.kol + fore[1]];
    grepp.lage = vridMedurs(grepp.lage);
    flyttaTill(grepp, halls);
  }
  function spegelvand() {
    if (!grepp) return;
    const d = delMap.get(grepp.id)!;
    const fore = orienterad(d.form, grepp.lage)[grepp.index];
    const halls: Ruta = [grepp.rad + fore[0], grepp.kol + fore[1]];
    grepp.lage = spegla(grepp.lage);
    flyttaTill(grepp, halls);
  }
  function lagg() {
    if (!grepp || !prov || prov.lager === null) return;
    const ny: Lagd = { id: grepp.id, lage: grepp.lage, rad: grepp.rad, kol: grepp.kol, lager: prov.lager };
    const d = delMap.get(grepp.id)!;
    spara([...lagda.filter(l => l.id !== grepp!.id), ny]);
    meddelande = prov.lager === 2 ? `${d.namn} ligger ovanpå, i andra lagret.` : '';
    grepp = null;
  }
  function tillbaka() {
    if (!grepp) return;
    if (grepp.fran) spara(lagda.filter(l => l.id !== grepp!.id));
    grepp = null;
    meddelande = '';
  }
  function avbryt() {
    if (!grepp) return;
    grepp = null;                                  // en bit från tomten ligger kvar där den låg
    meddelande = '';
  }

  function tangent(e: KeyboardEvent) {
    const mal = e.target as HTMLElement;
    if (mal && ['INPUT', 'SELECT', 'TEXTAREA'].includes(mal.tagName)) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? gorOm() : angra(); return; }
    if (!grepp) return;
    const steg: Record<string, [number, number]> = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
    if (e.key === 'r' || e.key === 'R') vrid();
    else if (e.key === 'f' || e.key === 'F') spegelvand();
    else if (e.key === 'Enter') lagg();
    else if (e.key === 'Escape') avbryt();
    else if (e.key in steg && !grepp.lyfter) { grepp.rad += steg[e.key][0]; grepp.kol += steg[e.key][1]; grepp.overBrade = true; }
    else return;
    e.preventDefault();
  }

  function hjul(e: WheelEvent) {
    if (!grepp) return;
    e.preventDefault();
    vrid();
  }
  function hogerklick(e: MouseEvent) {
    if (!grepp) return;
    e.preventDefault();
    spegelvand();
  }

  // ------------------------------------------------------------------ lösaren
  const markNu = () => {
    const alla = granska(somBitar(lagda, delMap)).mark;
    return [...alla].map(n => [Math.floor(n / TOMT), n % TOMT] as Ruta);
  };
  const projektIn = () => projekt.map(p => ({ id: p.id, typ: p.typ, form: p.form }));

  async function garDet() {
    grepp = null;
    raknar = true;
    meddelande = 'Räknar …';
    await new Promise(r => setTimeout(r, 30));
    const alla = losa(markNu(), projektIn(), { alla: true, ms: 1500 });
    if (Object.keys(alla.placeringar).length) {
      meddelande = `Ja, alla ${projekt.length} projekt får plats på marken du har.`;
    } else {
      const max = losa(markNu(), projektIn(), { ms: 1500 });
      const n = Object.keys(max.placeringar).length;
      meddelande = alla.fullstandig
        ? `Nej, som mest får ${n} av ${projekt.length} projekt plats. Resten går till projektbanken.`
        : `Minst ${n} av ${projekt.length} får plats. Det finns för många möjligheter för att räkna klart.`;
    }
    raknar = false;
  }

  async function visaLosning() {
    grepp = null;
    raknar = true;
    meddelande = 'Räknar …';
    await new Promise(r => setTimeout(r, 30));
    const l = losa(markNu(), projektIn(), { ms: 2000 });
    const mark = lagda.filter(x => delMap.get(x.id)!.typ === 'MARK');
    const nya = Object.entries(l.placeringar).map(([id, p]) => ({ id, lager: p.lager, ...lagdFran(delMap.get(id)!.form, p.celler) }));
    spara([...mark, ...nya]);
    const utanfor = projekt.length - nya.length;
    meddelande = utanfor
      ? `Så här får ${nya.length} av ${projekt.length} plats. ${utanfor} projekt går till banken. Ångra för att ta tillbaka ditt eget försök.`
      : `Så här får alla ${projekt.length} plats. Ångra för att ta tillbaka ditt eget försök.`;
    raknar = false;
  }

  function tomProjekten() {
    grepp = null;
    spara(lagda.filter(l => delMap.get(l.id)!.typ === 'MARK'));
    meddelande = 'Alla projekt är tillbaka i handen. Markexpansionerna ligger kvar.';
  }

  const hallerText = $derived(hallen
    ? `${hallen.namn} · ${hallen.form.length} rutor${hallen.typ !== 'MARK' && BOSTAD.has(hallen.typ) ? ' · får ligga ovanpå' : ''}`
    : '');
</script>

<svelte:window onkeydown={tangent} onresize={mattSkarm} />

<div class="pussel" class:haller={!!grepp}>
  <section class="bord" aria-label="Tomten">
    <div class="verktyg" role="toolbar" aria-label="Biten du håller">
      <!-- knapparna för biten man håller finns alltid, så att man ser att man kan vrida och spegla -->
      <button type="button" onclick={vrid} disabled={!grepp} title="Vrid (R)">⟳ Vrid</button>
      <button type="button" onclick={spegelvand} disabled={!grepp} title="Spegla (F)">⇋ Spegla</button>
      {#if grepp}
        <button type="button" class="lagg" onclick={lagg} disabled={!prov || prov.lager === null} title="Lägg (Enter)">Lägg</button>
        <button type="button" onclick={tillbaka} title="Tillbaka till handen">Till handen</button>
        <span class="haller-namn">{hallerText}</span>
      {:else}
        <button type="button" onclick={angra} disabled={!historik.length} title="Ångra (Ctrl+Z)">Ångra</button>
        <button type="button" onclick={gorOm} disabled={!framtid.length} title="Gör om (Ctrl+Shift+Z)">Gör om</button>
        {#if projekt.length}
          <button type="button" onclick={garDet} disabled={raknar}>Går det?</button>
          <button type="button" onclick={visaLosning} disabled={raknar}>Visa en lösning</button>
          <button type="button" onclick={tomProjekten} disabled={!lagdaProjekt.length}>Töm tomten</button>
        {/if}
        {#if lamnaIn}
          {@const hinder = lamnaKrav ? lamnaKrav(lagda) : null}
          <button type="button" class="lamna" onclick={() => lamnaIn!(lagda.map(l => ({ ...l })))} disabled={!!hinder || raknar}
                  title={hinder ?? ''}>{lamnaText}</button>
        {/if}
        <button type="button" aria-pressed={doljUppe} onclick={() => (doljUppe = !doljUppe)} disabled={!finnsUppe && !doljUppe}
                title="Dölj bostäderna i andra lagret för att se projekten under">{doljUppe ? 'Visa lager 2' : 'Dölj lager 2'}</button>
      {/if}
    </div>

    <svg
      bind:this={svg}
      class="tomt"
      viewBox="{ram.k0 * S - 4} {ram.r0 * S - 4} {ram.n * S + 8} {ram.n * S + 8}"
      role="application"
      aria-label="Tomten, 16 gånger 16 rutor"
      onpointerdown={tryckPaTomten}
      onwheel={hjul}
      oncontextmenu={hogerklick}
    >
      <defs>
        <filter id="lyft" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="3" dy="4" stdDeviation="2.5" flood-color="#1d2a30" flood-opacity="0.45" />
        </filter>
      </defs>
      <rect x="-4" y="-4" width={TOMT * S + 8} height={TOMT * S + 8} rx="6" class="tomtyta" />
      {#each Array(TOMT + 1) as _, i}
        <line x1={i * S} y1="0" x2={i * S} y2={TOMT * S} class="linje" />
        <line x1="0" y1={i * S} x2={TOMT * S} y2={i * S} class="linje" />
      {/each}

      <!-- marken: grundmark och lagda markexpansioner -->
      {#each markRutor as [r, k]}
        <rect x={k * S + 1.5} y={r * S + 1.5} width={S - 3} height={S - 3} fill={farg('MARK')} class:grund={grundmark.has(nyckel(r, k))} />
      {/each}

      <!-- Bitarna på tomten tas med pekaren; tangentbordet når samma handlingar via handen och
           R/F/pilar/Enter, därför är rutorna inte egna knappar. -->
      <!-- projekt: lager 1, sedan lager 2 ovanpå -->
      {#each doljUppe ? [1] : [1, 2] as lager}
        {#each ovriga.filter(l => l.lager === lager && delMap.get(l.id)!.typ !== 'MARK') as l (l.id)}
          {@const d = delMap.get(l.id)!}
          {@const c = cellerFor(d.form, l.lage, l.rad, l.kol)}
          {@const etikett = lager === 2 || doljUppe ? c[0] : c.find(([r, k]) => !uppeRutor.has(nyckel(r, k)))}
          <g class="bit" class:uppe={lager === 2} filter={lager === 2 ? 'url(#lyft)' : undefined}
             transform={lager === 2 ? 'translate(-3 -3)' : undefined}>
            <title>{d.namn} ({typnamn[d.typ]}{lager === 2 ? ', ovanpå' : ''})</title>
            {#each c as [r, k], i}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <rect x={k * S} y={r * S} width={S} height={S} class="fog" onpointerdown={e => lyftFranTomten(e, l, i)} />
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <rect x={k * S + 2} y={r * S + 2} width={S - 4} height={S - 4} fill={farg(d.typ)}
                    onpointerdown={e => lyftFranTomten(e, l, i)} />
            {/each}
            <path d={kontur(c)} class="kontur" />
            {#if etikett}
              <text x={etikett[1] * S + S / 2} y={etikett[0] * S + S / 2 + 6} class="bokstav">{bokstav[d.typ]}{lager === 2 ? '²' : ''}</text>
            {/if}
          </g>
        {/each}
      {/each}

      <!-- markexpansioner som går att lyfta (osynliga ytor ovanpå den gröna marken) -->
      {#each ovriga.filter(l => delMap.get(l.id)!.typ === 'MARK') as l (l.id)}
        {@const d = delMap.get(l.id)!}
        {@const mc = cellerFor(d.form, l.lage, l.rad, l.kol)}
        <g class="bit markbit">
          <title>Markexpansion, {d.form.length} rutor ({tal(d.form.length * 250)} kvm BYA)</title>
          <path d={kontur(mc)} class="markkontur" />
          {#each mc as [r, k], i}
            {#if !g.lager1.has(nyckel(r, k))}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <rect x={k * S + 1.5} y={r * S + 1.5} width={S - 3} height={S - 3} class="greppyta" onpointerdown={e => lyftFranTomten(e, l, i)} />
            {/if}
          {/each}
        </g>
      {/each}

      <!-- biten man håller -->
      {#if grepp && hallen && grepp.overBrade}
        <g class="skugga" class:ok={prov?.lager !== null && prov !== null} class:lyfter={grepp.lyfter}>
          {#each skugga as [r, k], i}
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <rect x={k * S} y={r * S} width={S} height={S} class="fog" onpointerdown={e => greppaSkuggan(e, i)} />
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <rect x={k * S + 2} y={r * S + 2} width={S - 4} height={S - 4} fill={farg(hallen.typ)}
                  class:dalig={prov?.daliga.has(nyckel(r, k))} onpointerdown={e => greppaSkuggan(e, i)} />
          {/each}
          <path d={kontur(skugga)} class="kontur" />
        </g>
      {/if}
    </svg>

    <p class="meddelande" role="status" aria-live="polite">{meddelande || (grepp ? '' : iHanden.length
      ? 'Tryck på en bit i handen för att ta upp den. Då kan du vrida, spegla och flytta den.'
      : 'Tryck på en bit på tomten för att flytta, vrida eller spegla den.')}</p>
  </section>

  <aside class="hand" aria-label="Handen">
    <dl class="siffror">
      <div><dt>Placerade</dt><dd>{lagdaProjekt.length} av {projekt.length}</dd></div>
      <div><dt>BYA</dt><dd>{tal(bya)} kvm</dd></div>
      <div><dt>BTA</dt><dd>{tal(bta)} kvm</dd></div>
      <div><dt>Mark</dt><dd>{tal(g.mark.size * 250)} kvm</dd></div>
    </dl>

    <div class="handlista">
    {#each [['MARK', 'Markexpansioner'], ['PROJEKT', 'Projekt att placera']] as [grupp, rubrik]}
      {@const lista = iHanden.filter(d => (d.typ === 'MARK') === (grupp === 'MARK'))}
      {#if lista.length}
        <h3>{rubrik}</h3>
        <ul>
          {#each lista as d (d.id)}
            <li>
              <button type="button" class="kort" class:vald={grepp?.id === d.id}
                      style="--typ:{farg(d.typ)};--ljus:{fargar[d.typ]?.ljus ?? '#fff'}"
                      onpointerdown={e => lyftUrHanden(e, d)}
                      onkeydown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); valjMedTangent(d); } }}>
                {#if d.bild}<img src={d.bild} alt="" loading="lazy" />{/if}
                <span class="text">
                  <span class="namn">{d.namn}</span>
                  <span class="fakta">{typnamn[d.typ]} · {d.form.length} rutor{d.bta ? ` · ${tal(d.bta)} kvm BTA` : d.bya ? ` · ${tal(d.bya)} kvm BYA` : ''}</span>
                </span>
                <Minibit form={d.form} farg={farg(d.typ)} storlek={11} />
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    {/each}
    {#if !iHanden.length}
      <p class="klart">Allt är placerat.</p>
    {/if}
    </div>

    <details class="regler">
      <summary>Reglerna (4.3)</summary>
      <ul>
        <li>Allt ska ligga på marken: grundmarken 4 × 4 plus markexpansioner.</li>
        <li>Markexpansioner läggs kant i kant med marken.</li>
        <li>Projekt får inte överlappa varandra i samma lager.</li>
        <li>Bostäder (BRF, hyresrätt) får ligga direkt på marken eller ovanpå andra projekt. Ovanpå ska hela biten vila på projekt, utan hål.</li>
        <li>Det som inte får plats placeras inte och går till projektbanken.</li>
      </ul>
      <p class="tangenter">Håller du en bit: <kbd>R</kbd> eller hjulet vrider, <kbd>F</kbd> eller högerklick speglar, pilarna flyttar, <kbd>Enter</kbd> lägger, <kbd>Esc</kbd> släpper. <kbd>Ctrl</kbd>+<kbd>Z</kbd> ångrar.</p>
    </details>
  </aside>
</div>

{#if grepp?.lyfter && !grepp.overBrade && hallen}
  <div class="flygande" style="left:{grepp.x}px;top:{grepp.y}px">
    <Minibit form={hallen.form} lage={grepp.lage} farg={farg(hallen.typ)} storlek={skarmRuta} />
  </div>
{/if}

<style>
  .pussel {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(260px, 340px);
    gap: 20px;
    align-items: start;
  }
  .handlista { display: grid; gap: 10px; }
  .bord { display: grid; gap: 10px; min-width: 0; }
  .verktyg {
    display: flex; flex-wrap: wrap; gap: 6px; align-items: center; min-height: 40px;
  }
  .verktyg button {
    font: inherit; font-weight: 600; font-size: 14px; letter-spacing: .02em;
    padding: 8px 12px; border-radius: 4px; border: 1px solid var(--linje-stark);
    background: var(--panel); color: var(--black); cursor: pointer;
  }
  .verktyg button:hover:not(:disabled) { background: var(--panel-mork); }
  .verktyg button:disabled { opacity: .45; cursor: default; }
  .verktyg button.lagg:not(:disabled) { background: var(--ok); border-color: var(--ok); color: #fff; }
  .verktyg button.lamna { background: var(--pu); border-color: var(--pu-mork); }
  .verktyg button.lamna:not(:disabled):hover { background: var(--pu-mork); color: #fff; }
  .verktyg button:focus-visible, .kort:focus-visible { outline: 3px solid var(--pu); outline-offset: 2px; }
  .haller-namn { font-weight: 600; margin-left: 4px; color: var(--black); flex-basis: 100%; }

  .tomt { width: 100%; max-width: 680px; height: auto; display: block; touch-action: none; user-select: none; }
  .tomtyta { fill: var(--tomt); }
  .linje { stroke: var(--tomt-linje); stroke-width: 1; }
  rect.grund { stroke: rgba(255, 255, 255, .0); }
  .fog { fill: #fff; }
  .kontur { fill: none; stroke: var(--black); stroke-width: 3; stroke-linecap: square; pointer-events: none; }
  .bit rect { cursor: grab; }
  .greppyta { fill: transparent; cursor: grab; }
  .markkontur { fill: none; stroke: #5d7a2c; stroke-width: 2; stroke-dasharray: 5 4; pointer-events: none; }
  .uppe rect:not(.fog) { filter: brightness(1.25) saturate(1.1); }
  .verktyg button[aria-pressed="true"] { background: var(--black); color: var(--panel); border-color: var(--black); }
  .bokstav { font: 700 17px var(--typsnitt); fill: #fff; text-anchor: middle; pointer-events: none; opacity: .9; }
  .skugga { opacity: .9; cursor: grab; }
  .skugga.lyfter { cursor: grabbing; }
  .skugga .fog { fill: var(--fel); }
  .skugga.ok .fog { fill: var(--ok); }
  .skugga rect.dalig { fill: var(--fel) !important; stroke: #fff; stroke-width: 2; stroke-dasharray: 4 3; }
  @media (prefers-reduced-motion: no-preference) {
    .skugga rect { transition: fill .12s; }
  }

  .meddelande { min-height: 1.4em; margin: 0; color: var(--black); font-size: 15px; max-width: 62ch; }

  .hand { display: grid; gap: 10px; }
  .siffror {
    display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; margin: 0;
    background: var(--linje-stark); border: 1px solid var(--linje-stark); border-radius: 4px; overflow: hidden;
  }
  .siffror div { background: var(--panel); padding: 8px 10px; display: grid; gap: 2px; }
  .siffror dt { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--dampad); }
  .siffror dd { margin: 0; font-weight: 700; font-size: 18px; font-variant-numeric: tabular-nums; }
  .hand h3 { margin: 8px 0 0; font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--black); }
  .hand ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  .kort {
    width: 100%; display: flex; align-items: center; gap: 10px; padding: 6px 10px 6px 6px; text-align: left;
    font: inherit; color: var(--black); background: var(--ljus); border: 1px solid transparent;
    border-left: 6px solid var(--typ); border-radius: 4px; cursor: grab; touch-action: none; user-select: none;
  }
  .kort:hover { border-color: var(--typ); }
  .kort.vald { opacity: .45; }
  .kort img {
    width: 44px; height: 38px; object-fit: cover; flex: none;
    clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%);
  }
  .text { display: grid; gap: 1px; flex: 1; min-width: 0; }
  .namn { font-weight: 700; font-size: 15px; }
  .fakta { font-size: 12.5px; color: var(--dampad); }
  .klart { margin: 0; font-weight: 600; }
  .regler { background: var(--panel); border-radius: 4px; padding: 8px 12px; font-size: 14px; }
  .regler summary { cursor: pointer; font-weight: 700; }
  .regler ul { list-style: disc; padding-left: 18px; margin: 8px 0; display: grid; gap: 4px; }
  .tangenter { margin: 6px 0 0; color: var(--dampad); }
  kbd { font: 600 12px var(--typsnitt); border: 1px solid var(--linje-stark); border-bottom-width: 2px; border-radius: 3px; padding: 0 4px; background: #fff; }

  .flygande { position: fixed; pointer-events: none; transform: translate(-50%, -50%); opacity: .85; z-index: 10; filter: drop-shadow(2px 4px 4px rgba(29, 42, 48, .4)); }
  /* Mobilen: en spalt, handen direkt ovanför tomten som en rad att svepa i, verktygen fästa överst. */
  @media (max-width: 820px) {
    .pussel { grid-template-columns: minmax(0, 1fr); gap: 10px; }
    .bord, .hand { display: contents; }
    .verktyg { order: 1; position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5;
               background: var(--panel); padding: 6px 0; }
    .handlista { order: 2; }
    .tomt { order: 3; }
    .meddelande { order: 4; }
    .siffror { order: 5; }
    .regler { order: 6; }
    .handlista ul { display: flex; overflow-x: auto; gap: 8px; padding-bottom: 4px; scroll-snap-type: x proximity; }
    .handlista li { flex: 0 0 min(78%, 260px); scroll-snap-align: start; }
    .handlista h3 { margin-top: 0; }
    .kort { touch-action: pan-x; }
  }
</style>
