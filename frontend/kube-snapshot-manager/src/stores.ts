import { writable } from 'svelte/store'
import ReconnectingWebSocket from 'reconnecting-websocket';

export const events = writable([])


const MAX_EVENTS = 10

// add in front and limit to 10
export const addEvent = (event) => {
	events.update((events) => {
		events.unshift(event)
		return events.slice(0, MAX_EVENTS)
	})
}

let _ws

export const connectWS = () => {
  events.subscribe((evts) => window.evts = evts)
	if (_ws) return
  _ws = new ReconnectingWebSocket(`ws://${window.location.host}/api/ws`)
  _ws.addEventListener('message', (event) => {
    addEvent(JSON.parse(event.data))
  })
}
