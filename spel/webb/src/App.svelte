<script lang="ts">
  // Enkel router på #-länkar (fungerar på vilken server som helst, även som statisk sida).
  //   #/                      nytt parti eller gå med
  //   #/parti/{id}            välj kvarter
  //   #/parti/{id}/{kvarter}  spela
  //   #/pussel                prova kvarterspusslet
  //   #/resultat/{namn,namn}  bara resultat: för in slutsiffrorna, appen räknar poängen
  import Pusselprov from './sidor/Pusselprov.svelte';
  import Resultat from './sidor/Resultat.svelte';
  import Spela from './sidor/Spela.svelte';
  import Start from './sidor/Start.svelte';

  let hash = $state(location.hash);
  const vag = $derived(hash.replace(/^#\/?/, '').split('/').map(decodeURIComponent));
</script>

<svelte:window onhashchange={() => (hash = location.hash)} />

{#if vag[0] === 'parti' && vag[1]}
  {#key `${vag[1]}/${vag[2] ?? ''}`}
    <Spela id={vag[1]} kvarter={vag[2] || undefined} />
  {/key}
{:else if vag[0] === 'resultat' && vag[1]}
  {#key vag[1]}<Resultat namn={vag[1].split(',').filter(Boolean)} />{/key}
{:else if vag[0] === 'pussel'}
  <Pusselprov />
{:else}
  <Start />
{/if}
