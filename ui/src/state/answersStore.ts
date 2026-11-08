import { create } from 'zustand'
import type { SessionAnswer, SessionAnswers } from '../time/timeview.ts'

interface AnswersState {
  answers: SessionAnswers
  // Items with a reply request in flight. Held here, not in a component, so selecting another item and
  // coming back cannot start a second POST for the same item (WR-09).
  inflight: Readonly<Record<string, true>>
  // Items the server said are already answered (409). Their buttons stay hidden (WR-03).
  conflicts: Readonly<Record<string, true>>
  begin: (id: string) => boolean
  end: (id: string) => void
  markConflict: (id: string) => void
  record: (id: string, answer: string, answeredAt: string, note?: string) => void
}

// In-memory only (D-21, T-02-16): never written to local or session storage, never logged. A page reload
// clears it, and in mock mode the item then returns to pending (documented behaviour). The note is kept
// only so it can be shown back as text; it is never rendered as markup.
export const useAnswersStore = create<AnswersState>((set, get) => ({
  answers: {},
  inflight: {},
  conflicts: {},
  // Synchronous check-and-set: returns false when a request for this item is already in flight.
  begin: (id) => {
    if (Object.hasOwn(get().inflight, id)) return false
    set((s) => ({ inflight: { ...s.inflight, [id]: true } }))
    return true
  },
  end: (id) =>
    set((s) => {
      const { [id]: _done, ...rest } = s.inflight
      return { inflight: rest }
    }),
  markConflict: (id) => set((s) => ({ conflicts: { ...s.conflicts, [id]: true } })),
  record: (id, answer, answeredAt, note) =>
    set((s) => {
      if (Object.hasOwn(s.answers, id)) return s // at most one reply per item per session
      const entry: SessionAnswer = { answer, answered_at: answeredAt }
      if (note !== undefined && note.trim() !== '') entry.note = note.trim()
      return { answers: { ...s.answers, [id]: entry } }
    }),
}))
