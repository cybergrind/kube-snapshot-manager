import { writable } from 'svelte/store'
import ReconnectingWebSocket from 'reconnecting-websocket'

export const events = writable([])
export const volumes = writable([])

const MAX_EVENTS = 10

// add in front and limit to 10
export const addEvent = (event) => {
	events.update((events) => {
		events.unshift(event)
		return events.slice(0, MAX_EVENTS)
	})
	if (event.type === 'volumes') {
		volumes.update(() => event.volumes)
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
