<script lang="ts">
	import Counter from './Counter.svelte'
	import { onMount } from 'svelte'
	import { runAlert } from './helpers.ts'
	import { events, connectWS } from '../stores.ts'
	onMount(() => {
		runAlert()
		connectWS()
	})
</script>

<svelte:head>
	<title>EKS Snapshot Manager</title>
</svelte:head>

<section>
	<h1>EKS Snapshot Manager</h1>

	{#if $events.length > 0}
		<div>Last event is {JSON.stringify($events[0])}</div>
	{:else}
		<div>There are no events</div>
	{/if}
	<Counter />
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
