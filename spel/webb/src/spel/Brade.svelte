<script lang="ts">
  // PU-brädet (Skede 1) med kvarterens pjäser. Bilden är det tryckta brädet med klistermärkena;
  // rutorna ligger medsols från Stadsbyggnadskontoret i hörnet nere till höger (motor/pu.py BRADE).
  // När ett kvarter flyttar går pjäsen ruta för ruta, så att man ser vägen den tar.

  let { kvarter, jag, aktiv = null, bank = 0 }: {
    kvarter: { namn: string; position?: number; ruta?: string }[];
    jag: string;
    aktiv?: string | null;
    bank?: number;
  } = $props();

  const SIDA = 1103;                                   // bildens storlek i pixlar
  const RUTOR = 24;
  const mitt = [264, 408, 552, 696, 840];              // rutornas mittlinjer längs en sida
  const KANT = 118, MOT = 985;                         // hörnrutornas mitt

  /** Rutans mittpunkt på bilden: 0 = Stadsbyggnadskontoret, sedan medsols. */
  function punkt(i: number): [number, number] {
    const n = ((i % RUTOR) + RUTOR) % RUTOR;
    const sida = Math.floor(n / 6), steg = n % 6;
    if (steg === 0) return [[MOT, MOT], [KANT, MOT], [KANT, KANT], [MOT, KANT]][sida] as [number, number];
    const t = steg - 1;
    if (sida === 0) return [mitt[4 - t], MOT];        // nederkanten, åt vänster
    if (sida === 1) return [KANT, mitt[4 - t]];       // vänsterkanten, uppåt
    if (sida === 2) return [mitt[t], KANT];           // överkanten, åt höger
    return [MOT, mitt[t]];                            // högerkanten, nedåt
  }

  const FARGER = ['#1d2a30', '#d9822b', '#2f6fb0', '#b23a48'];
  const farg = (namn: string) => FARGER[Math.max(0, kvarter.findIndex(k => k.namn === namn)) % FARGER.length];

  // pjäsernas visade position; går ett steg i taget mot den riktiga
  let visad = $state<Record<string, number>>({});
  const snabb = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  $effect(() => {
    for (const k of kvarter) if (!(k.namn in visad)) visad[k.namn] = k.position ?? 0;
    const tid = setInterval(() => {
      for (const k of kvarter) {
        const mal = k.position ?? 0, nu = visad[k.namn] ?? mal;
        if (nu !== mal) visad[k.namn] = snabb ? mal : (nu + 1) % RUTOR;
      }
    }, 170);
    return () => clearInterval(tid);
  });

  /** Pjäser på samma ruta läggs bredvid varandra. */
  const pjaser = $derived.by(() => {
    const per = new Map<number, string[]>();
    for (const k of kvarter) {
      const i = visad[k.namn] ?? k.position ?? 0;
      per.set(i, [...(per.get(i) ?? []), k.namn]);
    }
    const ut: { namn: string; x: number; y: number }[] = [];
    for (const [i, namn] of per) {
      const [x, y] = punkt(i);
      namn.forEach((n, j) => {
        const d = namn.length === 1 ? [0, 0] : [[-28, -28], [28, -28], [-28, 28], [28, 28]][j % 4];
        ut.push({ namn: n, x: x + d[0], y: y + d[1] });
      });
    }
    return ut;
  });
</script>

<figure class="brade">
  <img src="brade/pu.jpg" alt="PU-brädet" width={SIDA} height={SIDA} />
  <svg viewBox="0 0 {SIDA} {SIDA}" aria-hidden="true">
    {#if bank}
      <g transform="translate(726 700)">
        <rect x="-70" y="-24" width="140" height="48" rx="24" class="bank" />
        <text y="9" class="banktext">{bank} i banken</text>
      </g>
    {/if}
    {#each pjaser as p (p.namn)}
      <g class="pjas" class:aktiv={p.namn === aktiv} style="transform: translate({p.x}px, {p.y}px)">
        {#if p.namn === aktiv}<circle r="46" class="ring" />{/if}
        <circle r="34" fill={farg(p.namn)} class:jag={p.namn === jag} />
        <text y="12" class="bokstav">{p.namn.slice(0, 1).toUpperCase()}</text>
      </g>
    {/each}
  </svg>
  <figcaption>
    {#each kvarter as k (k.namn)}
      <span><i style="background:{farg(k.namn)}"></i>{k.namn}{k.namn === jag ? ' (ni)' : ''}{k.ruta ? ` · ${k.ruta.toLowerCase()}` : ''}</span>
    {/each}
  </figcaption>
</figure>

<style>
  .brade { margin: 0 0 12px; position: relative; display: grid; gap: 6px; }
  img { width: 100%; height: auto; display: block; border-radius: 6px; }
  svg { position: absolute; top: 0; left: 0; width: 100%; height: auto; aspect-ratio: 1; pointer-events: none; }
  .pjas { filter: drop-shadow(0 4px 4px rgba(29, 42, 48, .45)); }
  @media (prefers-reduced-motion: no-preference) {
    .pjas { transition: transform .16s ease-out; }
    .ring { animation: puls 1.4s ease-in-out infinite; transform-origin: center; }
  }
  @keyframes puls { 50% { opacity: .35; } }
  circle.jag { stroke: #fff; stroke-width: 7; }
  .ring { fill: none; stroke: #fff; stroke-width: 6; }
  .bokstav { font: 700 34px var(--typsnitt); fill: #fff; text-anchor: middle; }
  .bank { fill: var(--black); opacity: .85; }
  .banktext { font: 700 22px var(--typsnitt); fill: #fff; text-anchor: middle; }
  figcaption { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 13.5px; color: var(--black); }
  figcaption span { display: inline-flex; align-items: center; gap: 6px; }
  figcaption i { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
</style>
