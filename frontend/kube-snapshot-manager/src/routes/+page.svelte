<script lang='ts'>
	import Counter from './Counter.svelte';
</script>

<svelte:head>
	<title>EKS Snapshot Manager</title>
</svelte:head>

<section>
	<h1>EKS Snapshot Manager</h1>

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
