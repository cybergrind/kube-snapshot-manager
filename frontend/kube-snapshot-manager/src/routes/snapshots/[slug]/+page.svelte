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
</script>

<h1>Snapshot Info</h1>

{#if snapshot}
  <table>
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
  </table>
{/if}

<style>
  div {
    margin: 0.2rem;
  }
  table td {
    padding: 0.2rem;
    border: 1px solid #444;
  }
</style>
