import { writable } from 'svelte/store'
import ReconnectingWebSocket from 'reconnecting-websocket'
import { betterName } from './lib/volumes.ts'

export const events = writable([])
export const volumes = writable([])

export const allVolumes = writable([])
export const volumesFilter = writable('')

const MAX_EVENTS = 10

allVolumes.subscribe((allVolumes) => {
	const filterString = volumesFilter.get()

	volumes.set(
		allVolumes.filter((volume) => {
			if (filterString === '') {
				return true
			}

			return volume.name.includes(filterString)
		})
	)
})

// add in front and limit to 10
export const addEvent = (event) => {
	events.update((events) => {
		events.unshift(event)
		return events.slice(0, MAX_EVENTS)
	})
	if (event.type === 'volumes') {
		allVolumes.update(() => {
			event.volumes.map((volume) => {
				volume.name = betterName(volume)
			})
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
