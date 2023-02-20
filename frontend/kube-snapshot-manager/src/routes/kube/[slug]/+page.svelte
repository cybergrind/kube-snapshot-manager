<script lang="ts">
  import type { PageData } from './$types'
  export let data: PageData

  let slug
  $: slug = data.slug
</script>

<section>
	<h1>Kube {slug} </h1>
</section>
