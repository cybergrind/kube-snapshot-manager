<script lang="ts">
  import type { DebugSection } from '../types'
  export let name: string
  export let section: DebugSection

  $: values = section.values
  $: buttons = section.buttons

  console.log('DebugSection', { name, section, values, buttons })
</script>

<section>
<h2>{name}</h2>
<div>
  {#each Object.entries($values) as [key, value]}
    <div>{key} => {value}</div>
  {/each}
</div>
</section>
