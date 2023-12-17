<script lang="ts">
  import { onMount } from 'svelte'
  import { sendMsg, debugInfo } from '../../stores'
  import DebugSection from '../../components/DebugSection.svelte'

  $: sections = debugInfo.sections

  onMount(async () => {
    await sendMsg({ event: 'get_debug' })
  })
</script>

<section>
  <h1>Debug</h1>

  {#each Object.entries($sections) as [name, section]}
    <h2>{name}</h2>
    <DebugSection {name} {section} />
  {/each}
</section>

<style>
  section {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center;
    flex: 1;
  }

  h1 {
    width: 100%;
  }
</style>
