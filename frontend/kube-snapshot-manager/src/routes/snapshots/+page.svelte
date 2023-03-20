<script lang="ts">
  import { onMount } from 'svelte'
  import { sendMsg, allSnapshots } from '../../stores.ts'
  import Snapshots from '../../components/Snapshots.svelte'
  onMount(async () => {
    await sendMsg({ event: 'get_snapshots' })
  })

  let refreshing = false
  allSnapshots.subscribe(() => {
    refreshing = false
  })

  async function forceRefresh() {
    refreshing = true
    await sendMsg({ event: 'get_snapshots', force: true })
  }
</script>

<svelte:head>
  <title>EKS Snapshot Manager</title>
</svelte:head>

<section>
  <h1>Snapshots</h1>
  <span>
    <span>
      Here you can see all the snapshots that are currently available in your EKS cluster.
    </span>

    <button on:click={forceRefresh} disabled={refreshing}>
      {#if refreshing}
        <span>Refreshing...</span>
      {:else}
        <span>Refresh</span>
      {/if}
    </button>
  </span>

  <Snapshots />
</section>

<style>
  section {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    flex: 0.6;
  }

  h1 {
    width: 100%;
  }
</style>
