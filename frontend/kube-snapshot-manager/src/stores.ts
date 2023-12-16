import { writable } from 'svelte/store'

import ReconnectingWebSocket from 'reconnecting-websocket'
import { betterName } from './lib/volumes.ts'
import type { PV, DebugSection } from './types.ts'
import type { Writable } from 'svelte/store'
import type { DebugInfo } from './types'

export const events = writable([])
export const volumes = writable([])

export const allVolumes = writable([])
export const volumesFilter = writable('')
export const allSnapshots = writable<Record<string, any>>({})

// button sends {event: debugButton, action: <NAME>, **kwargs} 
export const debugInfo: DebugInfo = {
  names: writable<string[]>(['kube1', 'kube2']),
  sections: writable<Record<string, DebugSection>>({
    kube1: {
      values: writable<Record<string, any>>({ state: 'SLEEP' }),
      buttons: writable<Record<string, any>>({ trigger: { cluster: 'kube1' } })
    },
    kube2: {
      values: writable<Record<string, any>>({ state: 'SLEEP' }),
      buttons: writable<Record<string, any>>({ trigger: { cluster: 'kube2' } })
    }
  }),
})

export const kubeClusters = writable(['kube1', 'kube2'])
export const PVs: Writable<Record<string, Array<PV>>> = writable({})

export const loadLocalState = () => {
  const localVolumesFilter = localStorage.getItem('volumesFilter')
  if (localVolumesFilter) {
    volumesFilter.set(localVolumesFilter)
  }

  volumesFilter.subscribe((value) => {
    localStorage.setItem('volumesFilter', value)
  })
}

const MAX_EVENTS = 10
let _volumesFilter = ''
let _allVolumes = {}

const filterVolumes = () => {
  const filter = _volumesFilter.toLowerCase()
  if (filter === '') {
    volumes.set(_allVolumes)
  }
  const filteredVolumes = {}
  Object.entries(_allVolumes).forEach(([id, volume]) => {
    if (volume.name.includes(filter)) {
      filteredVolumes[id] = volume
    }
  })
  volumes.set(filteredVolumes)
}

volumesFilter.subscribe((value) => {
  _volumesFilter = value
  filterVolumes()
})
allVolumes.subscribe((value) => {
  _allVolumes = value
  filterVolumes()
})

// add in front and limit to 10
export const addEvent = (event) => {
  events.update((events) => {
    events.unshift(event)
    return events.slice(0, MAX_EVENTS)
  })
  console.log('Event: ', event)

  switch (event.event) {
    case 'volumes': {
      allVolumes.update(() => {
        console.log(event)
        Object.entries(event.volumes).forEach(([id, volume]) => {
          volume.name = betterName(volume)
        })
        console.log(event.volumes)
        return event.volumes
      })
      break
    }
    case 'snapshots': {
      allSnapshots.update(() => {
        return event.snapshots
      })
      break
    }
    case 'pvs': {
      PVs.update((old) => {
        return { ...old, [event.cluster]: event.pvs }
      })
      break
    }
    default: {
      console.log('Unknown event type: ', event.event, event)
    }
  }
}

let outMessages = []
let _ws

export const connectWS = () => {
  if (_ws !== undefined) return

  events.subscribe((evts) => (window.evts = evts))
  _ws = new ReconnectingWebSocket(`ws://${window.location.host}/api/ws`)
  _ws.addEventListener('message', (event) => {
    addEvent(JSON.parse(event.data))
  })
  _ws.addEventListener('open', () => {
    console.log('Connected. OutMessages: ', outMessages)
    outMessages.forEach((msg) => {
      sendMsg(msg)
    })
    outMessages = []
  })
}

export const sendMsg = async (msg) => {
  if (_ws === undefined) {
    outMessages.push(msg)
    return
  }
  _ws.send(JSON.stringify(msg))
}
