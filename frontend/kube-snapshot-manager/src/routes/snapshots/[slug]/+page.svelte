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

  async function toggleDeletionPolicy(cluster: string) {
    await sendMsg({ event: 'snapshot_toggle_deletion_policy', cluster, snap_id: snapshot.id })
  }
  async function fillTags(cluster: string) {
    const description = snapshot.description
    await sendMsg({ event: 'snapshot_fill_tags', cluster, snap_id: snapshot.id, description })
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
    <tr>
      <td>Tags</td>
      <td>
        {#each Object.entries(snapshot.tags) as [name, value]}
          <tr>
            <td>{name}</td>
            <td>{value}</td>
          </tr>
        {/each}
      </td>
    </tr>
    {#each snapshot.clusters as c}
      <tr>
        <td>{c.cluster}</td>
        <td>
          <table class="nested">
            <tr>
              <td>Deletion policy: </td>
              <td
                on:click={async () => {
                  await toggleDeletionPolicy(c.cluster)
                }}
              >
                {c.snapshot.deletion_policy}
              </td>
            </tr>
            {#if !snapshot.tags.namespace}
            <tr>
              <td />
              <td>
                <button
                  on:click={async () => {
                    await fillTags(c.cluster)
                  }}
                >
                  Fill tags
                </button>
              </td>
            </tr>
            {/if}
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
  table.main td {
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
