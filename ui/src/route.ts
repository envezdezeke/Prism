// Hash routes, no router library (D-02). Folder names contain spaces, ampersands and apostrophes,
// so the folder is always passed through encodeURIComponent.
export type Route = { view: 'pipeline' } | { view: 'inbox' } | { view: 'alerts' } | { view: 'deal'; folder: string }

const DEAL_PREFIX = '#/deals/'

export function buildHash(route: Route): string {
  switch (route.view) {
    case 'deal':
      return `${DEAL_PREFIX}${encodeURIComponent(route.folder)}`
    case 'inbox':
      return '#/inbox'
    case 'alerts':
      return '#/alerts'
    default:
      return '#/pipeline'
  }
}

// Anything unknown or malformed goes to the pipeline; this never throws (T-02-10).
export function parseHash(hash: string): Route {
  if (hash === '#/inbox') return { view: 'inbox' }
  if (hash === '#/alerts') return { view: 'alerts' }
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
