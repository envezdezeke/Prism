import { create } from 'zustand'
import { describeError, getClock } from '../api/client.ts'

type ClockStatus = 'idle' | 'loading' | 'ready' | 'error'

interface ClockState {
  now: string
  start: string
  end: string
  status: ClockStatus
  error: string
  load: () => Promise<void>
}

// The mock clock is stateless: GET /api/clock always returns the fixture time. The browser therefore
// owns the clock. It is read once here and never again (D-21); it is never a query.
export const useClockStore = create<ClockState>((set, get) => ({
  now: '',
  start: '',
  end: '',
  status: 'idle',
  error: '',
  load: async () => {
    const { status } = get()
    if (status === 'loading' || status === 'ready') return
    set({ status: 'loading', error: '' })
    try {
      const c = await getClock()
      set({ now: c.now, start: c.start, end: c.end, status: 'ready' })
    } catch (e) {
      set({ status: 'error', error: describeError(e) })
    }
  },
}))
