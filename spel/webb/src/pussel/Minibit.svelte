<script lang="ts">
  // En formbit i miniatyr, som formbilderna: färgade rutor med vita fogar.
  import { orienterad } from './kvarter';
  import type { Form } from './regler';

  let { form, lage = 0, farg, storlek = 12 }: { form: Form; lage?: number; farg: string; storlek?: number } = $props();
  const celler = $derived(orienterad(form, lage));
  const hojd = $derived(Math.max(...celler.map(c => c[0])) + 1);
  const bredd = $derived(Math.max(...celler.map(c => c[1])) + 1);
</script>

<svg class="minibit" width={bredd * storlek} height={hojd * storlek} viewBox="0 0 {bredd * storlek} {hojd * storlek}" aria-hidden="true">
  {#each celler as [r, k]}
    <rect x={k * storlek + 0.75} y={r * storlek + 0.75} width={storlek - 1.5} height={storlek - 1.5} fill={farg} />
  {/each}
</svg>

<style>
  .minibit { display: block; flex: none; }
</style>
