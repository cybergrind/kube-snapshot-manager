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
  values: Record<string, string>,
  buttons: Record<string, DebugButton>,
}

export interface DebugInfo {
  sections: Writable<Record<string, DebugSection>>,
}
