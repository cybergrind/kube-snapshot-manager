<script lang="ts">
	import { onMount } from 'svelte'
	import { sendMsg, allSnapshots } from '../../stores.ts'
	import Snapshots from '../../components/Snapshots.svelte'
	onMount(async () => {
		await sendMsg({ event: 'get_snapshots' })
	})
</script>

<svelte:head>
	<title>EKS Snapshot Manager</title>
</svelte:head>

<section>
	<h1>Snapshots</h1>
	<p>Here you can see all the snapshots that are currently available in your EKS cluster.</p>

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
