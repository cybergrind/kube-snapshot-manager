<script lang="ts">
  import type { PageData } from './$types'
  import PVs from '../../../components/PVs.svelte'
  import { sendMsg } from '../../../stores.ts'
  export let data: PageData

  let slug
  $: slug = data.slug
  $: sendMsg({ event: 'get_pvs', cluster: slug})

</script>

<section class="app">
	<h1>Kube {slug} </h1>
  <PVs {slug} />
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

