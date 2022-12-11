<script lang="ts">
	import { volumes } from '../stores.ts'

	function betterName(volume) {
		if (volume.tags.length === 0) {
			return volume.id
		}
		if (!volume.tags['kubernetes.io/created-for/pvc/name']) {
			if (volume.tags['Name']) {
				return `${volume.id} / ${volume.tags['Name']}`
			}
			return volume.id
		}
		const namespace = volume.tags['kubernetes.io/created-for/pvc/namespace']
		const name = volume.tags['kubernetes.io/created-for/pvc/name']
		return `${namespace} / ${name}`
	}
</script>

<section>
	<h4>Volumes [{Object.keys($volumes).length}]</h4>
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
					<td class="name">{betterName(volume)}</td>
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
