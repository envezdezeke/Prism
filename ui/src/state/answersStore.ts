import { create } from 'zustand'
import type { SessionAnswer, SessionAnswers } from '../time/timeview.ts'

interface AnswersState {
  answers: SessionAnswers
  record: (id: string, answer: string, answeredAt: string, note?: string) => void
}

// In-memory only (D-21, T-02-16): never written to local or session storage, never logged. A page reload
// clears it, and in mock mode the item then returns to pending (documented behaviour). The note is kept
// only so it can be shown back as text; it is never rendered as markup.
export const useAnswersStore = create<AnswersState>((set) => ({
  answers: {},
  record: (id, answer, answeredAt, note) =>
    set((s) => {
      if (Object.hasOwn(s.answers, id)) return s // at most one reply per item per session
      const entry: SessionAnswer = { answer, answered_at: answeredAt }
      if (note !== undefined && note.trim() !== '') entry.note = note.trim()
      return { answers: { ...s.answers, [id]: entry } }
    }),
}))
