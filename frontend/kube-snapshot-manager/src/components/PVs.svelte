<script lang="ts">
	import { PVs } from '../stores.ts'
  export let slug

  $: pvs = $PVs[slug] || {}
</script>

<section>
	<h4>PV [{Object.keys(pvs).length}] {slug} </h4>
	<table>
		<thead>
			<tr>
				<th>Name</th>
				<th>Capacity</th>
				<th>Status</th>
				<th>StorageClass</th>
				<th>Volume</th>
        <th>Claim</th>
        <th>Policy</th>
			</tr>
		</thead>
		<tbody>
			{#each Object.entries(pvs) as [id, pv]}
				<tr>
					<td>{pv.name}</td>
          <td>{pv.capacity}</td>
          <td>{pv.status}</td>
          <td>{pv.storage_class}</td>
          <td>{pv.volume}</td>
          <td>{pv.claim}</td>
          <td>{pv.reclaim_policy}</td>
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
