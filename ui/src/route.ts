// Hash routes, no router library (D-02). Folder names contain spaces, ampersands and apostrophes,
// so the folder is always passed through encodeURIComponent. Plan 04 adds the inbox and alerts routes.
export type Route = { view: 'pipeline' } | { view: 'deal'; folder: string }

const DEAL_PREFIX = '#/deals/'

export function buildHash(route: Route): string {
  return route.view === 'deal' ? `${DEAL_PREFIX}${encodeURIComponent(route.folder)}` : '#/pipeline'
}

// Anything unknown or malformed goes to the pipeline; this never throws (T-02-10).
export function parseHash(hash: string): Route {
  if (hash.startsWith(DEAL_PREFIX)) {
    try {
      const folder = decodeURIComponent(hash.slice(DEAL_PREFIX.length))
      if (folder !== '') return { view: 'deal', folder }
    } catch {
      // malformed escape sequence
    }
  }
  return { view: 'pipeline' }
}
