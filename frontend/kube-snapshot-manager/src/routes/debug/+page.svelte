<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { addWsCallback, deleteWsCallback, sendMsg, debugInfo } from '../../stores'
  import DebugSection from '../../components/DebugSection.svelte'

  $: sections = debugInfo.sections

  const callbackName = 'debug'
  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

  const subscribe = async () => {
    console.log('before sleep')
    await sleep(1000)
    console.log('send get_debug')
    await sendMsg({ event: 'get_debug' })
  }

  onMount(() => {
    addWsCallback(callbackName, subscribe)
  })
  onDestroy(() => {
    deleteWsCallback(callbackName)
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
