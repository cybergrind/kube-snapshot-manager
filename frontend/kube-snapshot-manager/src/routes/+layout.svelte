<script>
	import Header from './Header.svelte'
	import './styles.css'
	import { onMount } from 'svelte'
	import { connectWS, loadLocalState, kubeClusters } from '../stores.ts'
	onMount(() => {
		connectWS()
		loadLocalState()
	})
</script>

<div class="app">
	<Header />
	<main>
		<nav>
			<a href="/static">Volumes</a>
			<a href="/static/snapshots">Snapshots</a>
			{#each $kubeClusters as cluster}
				<a href="/static/kube/{cluster}">{cluster}</a>
			{/each}
      <a href="/static/debug">Debug</a>
		</nav>
		<slot />
	</main>

	<footer />
</div>

<style>
	nav a {
		padding-right: 5px;
		border-left: 1px solid #000;
		padding-left: 5px;
	}
	.app {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}

	main {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: 1rem;
		width: 100%;
		max-width: 64rem;
		margin: 0 auto;
		box-sizing: border-box;
	}

	footer {
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		padding: 12px;
	}

	footer a {
		font-weight: bold;
	}

	@media (min-width: 480px) {
		footer {
			padding: 12px 0;
		}
	}
</style>
