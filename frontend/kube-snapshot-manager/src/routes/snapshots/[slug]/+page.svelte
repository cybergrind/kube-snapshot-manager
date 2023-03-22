<script lang="ts">
  import type { PageData } from './$types'
  import PVs from '../../../components/PVs.svelte'
  import { sendMsg, allSnapshots } from '../../../stores'
  export let data: PageData

  let loaded = false

  $: slug = data.slug
  $: if (!$allSnapshots.length && !loaded) {
    sendMsg({ event: 'get_snapshots' })
    loaded = true
  }
  $: snapshot = $allSnapshots[slug]
  $: console.log(snapshot)

  async function toggleDeletionPolicy(cluster) {
    await sendMsg({event: 'snapshot_toggle_deletion_policy', cluster, snap_id: snapshot.id})
  }
</script>

<h1>Snapshot Info</h1>

{#if snapshot}
  <table class="main">
    <tr>
      <td>Id</td>
      <td>{snapshot.id}</td>
    </tr>
    <tr>
      <td>Description</td>
      <td>{snapshot.description}</td>
    </tr>
    <tr>
      <td>Progress</td>
      <td>[{snapshot.progress}]</td>
    </tr>
    <tr>
      <td>Size</td>
      <td>{snapshot.size}</td>
    </tr>
    {#each snapshot.clusters as c}
      <tr>
        <td>{c.cluster}</td>
        <td>
          <table class="nested">
            <tr>
              <td>Deletion policy: </td>
              <td on:click={async () => { await toggleDeletionPolicy(c.cluster)}}>{c.snapshot.deletion_policy}</td>
            </tr>
          </table>
        </td>
      </tr>
    {/each}
  </table>
{/if}

<style>
  div {
    margin: 0.2rem;
  }
  table.main  td {
    padding: 0.2rem;
    border: 1px solid #444;
  }
  table.nested:nth-child(odd) {
    border: 1px solid #444;
  }
  table.nested td {
    padding-left: 0.5rem;
    border: 0;
  }
</style>