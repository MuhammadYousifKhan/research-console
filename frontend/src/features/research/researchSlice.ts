import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'

type ResearchUiState = {
  selectedRunId: number | null
  sidebarOpen: boolean
}

const initialState: ResearchUiState = {
  selectedRunId: null,
  // On desktop the sidebar is always visible via CSS; this flag only drives
  // the mobile slide-in drawer.
  sidebarOpen: false,
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
  },
})

export const { selectRun, openSidebar, closeSidebar, toggleSidebar } = researchSlice.actions
export default researchSlice.reducer
