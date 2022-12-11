import { writable } from 'svelte/store'
import ReconnectingWebSocket from 'reconnecting-websocket'
import { betterName } from './lib/volumes.ts'

export const events = writable([])
export const volumes = writable([])

export const allVolumes = writable([])
export const volumesFilter = writable('')

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

	if (event.type === 'volumes') {
		allVolumes.update(() => {
			console.log(event)
			Object.entries(event.volumes).forEach(([id, volume]) => {
				volume.name = betterName(volume)
			})
			console.log(event.volumes)
			return event.volumes
		})
	}
}

let _ws

export const connectWS = () => {
	if (_ws !== undefined) return

	events.subscribe((evts) => (window.evts = evts))
	_ws = new ReconnectingWebSocket(`ws://${window.location.host}/api/ws`)
	_ws.addEventListener('message', (event) => {
		addEvent(JSON.parse(event.data))
	})
}
