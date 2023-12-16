import type { Writable } from "svelte/store"

export interface PV {
  name: string
  capacity: string
  access_modes: string[]
  reclaim_policy: string
  volume_mode: string
  status: string
  claim: string
  storage_class: string
  volume: string
}


export declare type DebugButton = Record<string, any>

export interface DebugSection {
  values: Writable<Record<string, string>>,
  buttons: Writable<Record<string, DebugButton>,
}

export interface DebugInfo {
  names: Writable<string[]>,
  sections: Writable<Record<string, DebugSection>>,
}
