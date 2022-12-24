<script lang="ts">
	import { allSnapshots } from '../stores.ts'
</script>

<section>
	<table>
		<thead>
			<tr>
				<td>Id</td>
				<td>Description</td>
				<td>Size</td>
				<td>Progress</td>
			</tr>
		</thead>
		<tbody>
			{#each Object.entries($allSnapshots) as [id, snapshot]}
				<tr>
					<td>{snapshot.id}</td>

					<td class="tooltip">
						{snapshot.description.slice(0, 16)}...
						<span class="tooltip-text">{snapshot.description}</span>
					</td>
					<td>{snapshot.size}</td>
					<td>{snapshot.progress}</td>
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
		padding-left: 4px;
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

	.tooltip {
		position: relative;
	}
	.tooltip-text {
		visibility: hidden;
		width: 380px;
		background-color: #444;
		color: #fff;
		text-align: center;
		border-radius: 6px;
		padding: 5px 0;
		position: absolute;
		z-index: 1;
		bottom: 125%;
		left: 50%;
		margin-left: -60px;
		opacity: 0;
		transition: opacity 0.3s;
	}
	.tooltip:hover .tooltip-text {
		visibility: visible;
		opacity: 1;
	}
</style>
