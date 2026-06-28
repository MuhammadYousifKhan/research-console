import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

import type {
  CitationsResponse,
  CreateResearchRequest,
  ResearchHistoryResponse,
  ResearchRun,
} from './types'

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://127.0.0.1:8000'

export const researchApi = createApi({
  reducerPath: 'researchApi',
  baseQuery: fetchBaseQuery({ baseUrl: API_BASE_URL }),
  tagTypes: ['History', 'Run'],
  endpoints: (builder) => ({
    getHistory: builder.query<ResearchHistoryResponse, number | void>({
      query: (limit = 30) => `/research?limit=${limit ?? 30}`,
      providesTags: (result) =>
        result
          ? [
              ...result.items.map((item) => ({ type: 'Run' as const, id: item.research_id })),
              { type: 'History' as const, id: 'LIST' },
            ]
          : [{ type: 'History' as const, id: 'LIST' }],
    }),
    getRun: builder.query<ResearchRun, number>({
      query: (id) => `/research/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Run', id }],
    }),
    getCitations: builder.query<CitationsResponse, number>({
      query: (id) => `/research/${id}/citations`,
      providesTags: (_result, _error, id) => [{ type: 'Run', id }],
    }),
    createResearch: builder.mutation<ResearchRun, CreateResearchRequest>({
      query: (body) => ({
        url: '/research',
        method: 'POST',
        body,
      }),
      // A new run changes the history list; refetch it.
      invalidatesTags: [{ type: 'History', id: 'LIST' }],
    }),
  }),
})

export const {
  useGetHistoryQuery,
  useGetRunQuery,
  useLazyGetRunQuery,
  useGetCitationsQuery,
  useCreateResearchMutation,
} = researchApi
