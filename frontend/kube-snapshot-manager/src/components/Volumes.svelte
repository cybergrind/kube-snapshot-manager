<script lang="ts">
  import { volumes, volumesFilter, sendMsg } from '../stores.ts'

  async function createSnapshot() {
    console.log('implement me')
  }
</script>

<section>
  <h4>Volumes [{Object.keys($volumes).length}]</h4>
  <input bind:value={$volumesFilter} />
  <table>
    <thead>
      <tr>
        <th>Name</th>
        <th>Size</th>
        <th>Snapshot</th>
        <th>Attached</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      {#each Object.entries($volumes) as [id, volume]}
        <tr>
          <td class="name">{volume.name}</td>
          <td>{volume.size}</td>
          <td
            >{#if volume.snapshots.length}
              <span class="green">Y</span>
            {:else}
              <span class="red">N</span>
            {/if}
          </td>
          <td
            >{#if volume.attachments.length}
              <span class="green">Y</span>
            {:else}
              <span class="red">N</span>
            {/if}
          </td>
          <td>
            <button on:click={() => createSnapshot(volume.name)}>Create Snapshot</button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  table {
    border-collapse: collapse;
    border-spacing: 0;
    min-width: 80vw;
  }
  td {
    border: 1px solid #ccc;
  }
  th {
    border: 1px solid #ccc;
    padding: 0px 4px 0px 4px;
  }
  td.name {
    size: 20em;
    padding: 0px 10px 0px 10px;
  }
  .red {
    color: red;
    size: 4em;
  }
  .green {
    color: green;
  }
</style>
