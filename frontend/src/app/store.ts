import { configureStore } from '@reduxjs/toolkit'

import { researchApi } from '../features/research/researchApi'
import researchUiReducer from '../features/research/researchSlice'

export const store = configureStore({
  reducer: {
    [researchApi.reducerPath]: researchApi.reducer,
    researchUi: researchUiReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(researchApi.middleware),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
