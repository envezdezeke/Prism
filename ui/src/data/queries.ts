import { useQueries, useQuery } from '@tanstack/react-query'
import { getAlerts, getDeal, getDeals, getInbox, describeError } from '../api/client.ts'
import type { DealDetail } from '../api/types.ts'

// One deal's detail. Shares the cache key with the board's per-deal queries, so a deal the board has
// already loaded opens with no extra request, and a failure here belongs to this deal alone (UI-04).
export function useDealDetail(folder: string) {
  return useQuery({
    queryKey: ['deal', folder],
    queryFn: () => getDeal(folder),
  })
}

// Inbox and alert lists. Same defaults as every query (no refetch on focus, never stale) and never the clock.
export function useInbox() {
  return useQuery({ queryKey: ['inbox'], queryFn: getInbox })
}

export function useAlerts() {
  return useQuery({ queryKey: ['alerts'], queryFn: getAlerts })
}

export function useDeals() {
  return useQuery({ queryKey: ['deals'], queryFn: getDeals })
}

// There is no bulk detail endpoint, and the time derivation needs every stage_log.
export function useDealDetails(folders: string[]) {
  return useQueries({
    queries: folders.map((folder) => ({
      queryKey: ['deal', folder],
      queryFn: () => getDeal(folder),
    })),
    combine: (results) => ({
      details: results.flatMap((r) => (r.data ? [r.data as DealDetail] : [])),
      isLoading: results.some((r) => r.isPending),
      errors: results.flatMap((r) => (r.error ? [describeError(r.error)] : [])),
      refetchFailed: () => results.forEach((r) => r.error && void r.refetch()),
    }),
  })
}
