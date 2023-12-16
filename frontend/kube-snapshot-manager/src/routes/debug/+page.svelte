<script lang="ts">
  import { onMount } from 'svelte'
  import { sendMsg, debugInfo } from '../../stores'

  onMount(async () => {
    await sendMsg({ event: 'get_debug' })
  })
</script>

<svelte:head>
  <title>EKS Snapshot Manager</title>
</svelte:head>

<section>
  <h1>Debug</h1>

  {#each $debugInfo.sections as sectionName}
    <h2>{sectionName}</h2>
  {/each}
</section>

<style>
  section {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center;
    flex: 1;
  }

  h1 {
    width: 100%;
  }
</style>
