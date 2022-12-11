<script lang="ts">
	import Counter from './Counter.svelte'
	import { onMount } from 'svelte'
	import { runAlert } from './helpers.ts'
	import { events } from '../stores.ts'
	import Volumes from '../components/Volumes.svelte'
	onMount(() => {
		runAlert()
	})

	let collapsed = true
</script>

<svelte:head>
	<title>EKS Snapshot Manager</title>
</svelte:head>

<section>
	<h1>EKS Snapshot Manager</h1>

	<Volumes />

	{#if $events.length > 0}
		{#if collapsed}
			<div on:click={() => (collapsed = false)}>Events count: {$events.length}</div>
		{:else}
			<div on:click={() => (collapsed = true)}>Last event is {JSON.stringify($events[0])}...</div>
		{/if}
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
