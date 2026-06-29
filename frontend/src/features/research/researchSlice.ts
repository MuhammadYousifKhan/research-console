import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'

import type { ExecutionStep } from './types'

type StreamStatus = 'idle' | 'streaming' | 'done' | 'error'

type ResearchUiState = {
  selectedRunId: number | null
  sidebarOpen: boolean
  // Live pipeline progress for the run currently being streamed.
  streamStatus: StreamStatus
  liveSteps: ExecutionStep[]
  streamError: string | null
  // Echo of the submitted request so the workspace can render a running
  // header (query + planned task count) before the run is persisted.
  streamQuery: string
  streamMaxTasks: number
}

const initialState: ResearchUiState = {
  selectedRunId: null,
  // On desktop the sidebar is always visible via CSS; this flag only drives
  // the mobile slide-in drawer.
  sidebarOpen: false,
  streamStatus: 'idle',
  liveSteps: [],
  streamError: null,
  streamQuery: '',
  streamMaxTasks: 0,
}

const researchSlice = createSlice({
  name: 'researchUi',
  initialState,
  reducers: {
    selectRun(state, action: PayloadAction<number | null>) {
      state.selectedRunId = action.payload
    },
    openSidebar(state) {
      state.sidebarOpen = true
    },
    closeSidebar(state) {
      state.sidebarOpen = false
    },
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen
    },
    streamStarted(state, action: PayloadAction<{ query: string; maxTasks: number }>) {
      state.streamStatus = 'streaming'
      state.liveSteps = []
      state.streamError = null
      state.streamQuery = action.payload.query
      state.streamMaxTasks = action.payload.maxTasks
    },
    streamStepReceived(state, action: PayloadAction<ExecutionStep>) {
      state.liveSteps.push(action.payload)
    },
    streamCompleted(state) {
      state.streamStatus = 'done'
    },
    streamFailed(state, action: PayloadAction<string>) {
      state.streamStatus = 'error'
      state.streamError = action.payload
    },
  },
})

export const {
  selectRun,
  openSidebar,
  closeSidebar,
  toggleSidebar,
  streamStarted,
  streamStepReceived,
  streamCompleted,
  streamFailed,
} = researchSlice.actions
export default researchSlice.reducer
