import { useMemo, useRef, useState } from 'react'
import { CircleAlert } from 'lucide-react'
import { ApiError, describeError, postReply, NOTE_MAX } from '../../api/client.ts'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useDeals, useInbox } from '../../data/queries.ts'
import { fmtDuration, fmtSimTime } from '../../lib/format.ts'
import { isClearedAnswer, optionLabel, requestTypeLabel } from '../../labels.ts'
import { personLabel, roleForRequest } from '../../people.ts'
import { useAnswersStore } from '../../state/answersStore.ts'
import { useClockStore } from '../../state/clockStore.ts'
import { inboxAt, simToMs } from '../../time/timeview.ts'
import type { InboxView, SessionAnswer, SessionAnswers } from '../../time/timeview.ts'
import type { InboxItem } from '../../api/types.ts'
import { Caption, DealLink, EmptyState, ErrorState, LoadingState, PageTitle } from './Primitives.tsx'

type Item = InboxView<InboxItem>
type Segment = 'pending' | 'answered'

interface DealName {
  name: string
  folder: string | null
}

// The legal name with the folder beneath it; the folder alone when the deal is not in the list.
function dealName(names: Map<string, string | null>, folder: string): DealName {
  const legal = names.get(folder)
  if (legal == null || legal === folder) return { name: folder, folder: null }
  return { name: legal, folder }
}

// Options that need a second, inline confirmation before they are sent (UI-SPEC answer flow).
const CONFIRM_OPTIONS = ['decline', 'release_hold']

function AnswerLine({ answer, at }: { answer: string; at: string }) {
  return (
    <div role="status" className="flex flex-wrap items-center gap-2 text-sm">
      <span>
        Answered: {optionLabel(answer)} · <span className="tabular-nums">{fmtSimTime(at)}</span>
      </span>
      {isClearedAnswer(answer) && <Badge variant="cleared">Approved</Badge>}
    </div>
  )
}

function Confirmation({
  option,
  name,
  disabled,
  onConfirm,
  onBack,
}: {
  option: string
  name: string
  disabled: boolean
  onConfirm: () => void
  onBack: () => void
}) {
  const release = option === 'release_hold'
  return (
    <div className="flex flex-col gap-2 border-t border-line pt-3">
      <h3 className="text-base font-semibold">{release ? `Release the fraud hold on ${name}?` : `Decline ${name}?`}</h3>
      <p className="text-base">
        {release
          ? 'This records a release at the current sim time. The deal stays frozen in the mock data.'
          : 'This records a decline at the current sim time.'}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button disabled={disabled} onClick={onConfirm}>
          {release ? 'Confirm release hold' : 'Confirm decline'}
        </Button>
        <Button variant="outline" disabled={disabled} onClick={onBack}>
          {release ? 'Keep the hold' : 'Back to the request'}
        </Button>
      </div>
    </div>
  )
}

// The selected request. Keyed by item id in the parent, so the note, the confirmation and any error
// belong to one request. Buttons are exactly the item's options (T-02-13); one reply per item per session.
function Pane({
  item,
  who,
  deal,
  now,
  session,
  onRefresh,
}: {
  item: Item
  who: { label: string; title: string }
  deal: DealName
  now: string
  session: SessionAnswer | undefined
  onRefresh: () => void
}) {
  const record = useAnswersStore((s) => s.record)
  const [note, setNote] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<{ text: string; retryable: boolean } | null>(null)
  const [confirm, setConfirm] = useState<string | null>(null)
  const [lastOption, setLastOption] = useState<string | null>(null)
  // A ref closes the gap between a click and the re-render that disables the buttons.
  const inFlight = useRef(false)

  const send = async (option: string): Promise<void> => {
    if (inFlight.current || item.answeredInSession || item.status === 'answered') return
    if (!item.options.includes(option)) return
    inFlight.current = true
    setSending(true)
    setError(null)
    setConfirm(null)
    setLastOption(option)
    const answeredAt = now // the UI clock at the click, never a time the API echoes
    try {
      await postReply(item.id, option, note)
      record(item.id, option, answeredAt, note)
    } catch (e) {
      // A failed or interrupted send writes nothing to the overlay: the item stays pending.
      if (e instanceof ApiError && e.status === 409) {
        setError({ text: 'This request was already answered. The list has been refreshed.', retryable: false })
        onRefresh()
      } else if (e instanceof ApiError && e.status === 422) {
        setError({ text: `The server rejected that option: ${e.message}`, retryable: false })
      } else {
        setError({ text: describeError(e), retryable: true })
      }
    } finally {
      inFlight.current = false
      setSending(false)
    }
  }

  const choose = (option: string): void => {
    if (CONFIRM_OPTIONS.includes(option)) setConfirm(option)
    else void send(option)
  }

  const answered = item.status === 'answered' && item.answer != null && item.answered_at != null
  const answerable = !answered && !item.answeredInSession

  return (
    <aside aria-label="Request" className="flex flex-col gap-3 rounded-md border border-line border-t-4 border-t-navy bg-surface p-4">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold">{deal.name}</p>
        {deal.folder !== null && <Caption>{deal.folder}</Caption>}
      </div>
      <h2 className="text-base font-bold text-navy">{requestTypeLabel(item.type)}</h2>
      <div className="flex flex-col gap-1 text-sm text-ink-2">
        <p className="tabular-nums">Sent {fmtSimTime(item.at)}</p>
        <p title={who.title}>To {who.label}</p>
      </div>
      <p className="text-base">{item.message}</p>

      {answered && <AnswerLine answer={item.answer as string} at={item.answered_at as string} />}

      {!answered && item.answeredInSession && session !== undefined && (
        <p className="text-sm text-ink-2">
          Answered in this session at <span className="tabular-nums">{fmtSimTime(session.answered_at)}</span>. The clock is set
          before that time.
        </p>
      )}

      {answerable && confirm !== null && (
        <Confirmation
          option={confirm}
          name={deal.name}
          disabled={sending}
          onConfirm={() => void send(confirm)}
          onBack={() => setConfirm(null)}
        />
      )}

      {answerable && confirm === null && (
        <div className="flex flex-col gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-ink-2">Note (optional)</span>
            <Input
              type="text"
              value={note}
              maxLength={NOTE_MAX}
              disabled={sending}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            {item.options.map((option, i) => (
              <Button
                key={option}
                variant={i === 0 ? 'default' : 'outline'}
                disabled={sending}
                onClick={() => choose(option)}
              >
                {optionLabel(option)}
              </Button>
            ))}
          </div>
        </div>
      )}

      {error !== null && (
        <div role="alert" className="flex items-start gap-2 text-sm text-ink">
          <CircleAlert className="mt-0.5 size-4 shrink-0 text-ink-2" aria-hidden="true" />
          <div className="flex flex-col gap-2">
            <p>{error.text}</p>
            {error.retryable && lastOption !== null && answerable && (
              <div>
                <Button variant="outline" size="sm" disabled={sending} onClick={() => void send(lastOption)}>
                  Retry
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </aside>
  )
}

function SegmentButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`h-10 rounded-t-sm border-b-4 px-4 text-sm ${
        active ? 'border-sky bg-navy font-bold text-surface' : 'border-transparent font-medium text-ink-2 hover:bg-subtle'
      }`}
    >
      {children}
    </button>
  )
}

export function InboxList({
  items,
  segment,
  names,
  nowMs,
  selectedId,
  onSelect,
}: {
  items: Item[]
  segment: Segment
  names: Map<string, string | null>
  nowMs: number
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <div className="rounded-md border border-line bg-surface">
      <Table>
        <TableHeader className="bg-navy [&_th]:text-xs [&_th]:font-bold [&_th]:tracking-wide [&_th]:text-surface [&_th]:uppercase">
          <TableRow className="border-navy hover:bg-transparent">
            <TableHead className="border-l-4 border-transparent">Age</TableHead>
            <TableHead>Deal</TableHead>
            <TableHead>Request</TableHead>
            <TableHead>To</TableHead>
            <TableHead>Message</TableHead>
            {segment === 'answered' && <TableHead>Answer</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => {
            const deal = dealName(names, item.deal)
            const who = personLabel(item.to, roleForRequest(item.type))
            const selected = item.id === selectedId
            return (
              <TableRow key={item.id} className={`cursor-pointer align-top ${selected ? 'bg-subtle' : ''}`} onClick={() => onSelect(item.id)}>
                <TableCell className={`border-l-4 whitespace-nowrap font-semibold tabular-nums ${selected ? 'border-navy' : 'border-transparent'}`}>
                  <button
                    type="button"
                    aria-pressed={selected}
                    aria-label={`Open ${requestTypeLabel(item.type)} for ${deal.name}`}
                    onClick={() => onSelect(item.id)}
                    className="text-left"
                  >
                    {fmtDuration(nowMs - simToMs(item.at))}
                  </button>
                </TableCell>
                <TableCell className="max-w-48">
                  <DealLink folder={item.deal}>
                    <span className="block truncate font-semibold" title={deal.name}>
                      {deal.name}
                    </span>
                  </DealLink>
                  {deal.folder !== null && (
                    <span className="block truncate text-xs text-ink-2" title={deal.folder}>
                      {deal.folder}
                    </span>
                  )}
                </TableCell>
                <TableCell className="whitespace-nowrap">{requestTypeLabel(item.type)}</TableCell>
                <TableCell className="whitespace-nowrap" title={who.title}>
                  {who.label}
                </TableCell>
                <TableCell className="max-w-64 truncate" title={item.message}>
                  {item.message}
                </TableCell>
                {segment === 'answered' && (
                  <TableCell className="whitespace-nowrap tabular-nums">
                    {item.answer == null ? null : optionLabel(item.answer)}
                    {item.answered_at != null && ` · ${fmtSimTime(item.answered_at)}`}
                  </TableCell>
                )}
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

// Pending first and oldest first; answered by answer time, newest first (UI-SPEC).
function splitInbox(view: Item[]): { pending: Item[]; answered: Item[] } {
  const pending = view.filter((i) => i.status === 'pending').sort((a, b) => simToMs(a.at) - simToMs(b.at))
  const answered = view
    .filter((i) => i.status === 'answered')
    .sort((a, b) => simToMs(b.answered_at as string) - simToMs(a.answered_at as string))
  return { pending, answered }
}

export function InboxScreen({
  items,
  names,
  now,
  answers,
  onRefresh,
}: {
  items: InboxItem[]
  names: Map<string, string | null>
  now: string
  answers: SessionAnswers
  onRefresh: () => void
}) {
  const [segment, setSegment] = useState<Segment>('pending')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const nowMs = simToMs(now)
  const when = fmtSimTime(now)
  const view = useMemo(() => inboxAt(items, nowMs, answers), [items, nowMs, answers])
  const { pending, answered } = useMemo(() => splitInbox(view), [view])
  const shown = segment === 'pending' ? pending : answered
  const selected = view.find((i) => i.id === selectedId)

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex border-b-2 border-navy">
          <SegmentButton active={segment === 'pending'} onClick={() => setSegment('pending')}>
            Pending <span className="tabular-nums">{pending.length}</span>
          </SegmentButton>
          <SegmentButton active={segment === 'answered'} onClick={() => setSegment('answered')}>
            Answered <span className="tabular-nums">{answered.length}</span>
          </SegmentButton>
        </div>
        {shown.length > 0 ? (
          <InboxList
            items={shown}
            segment={segment}
            names={names}
            nowMs={nowMs}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        ) : segment === 'pending' ? (
          <EmptyState heading="No pending requests.">
            {view.length === 0 ? `No requests have been sent as of ${when}.` : 'Everything is waiting on borrowers or the clock.'}
          </EmptyState>
        ) : (
          <EmptyState heading={`No answered requests as of ${when}.`} />
        )}
      </div>
      {selected === undefined ? (
        <aside aria-label="Request" className="rounded-md border border-line border-t-4 border-t-navy bg-surface p-4">
          <Caption>Select a request to read it and answer it.</Caption>
        </aside>
      ) : (
        <Pane
          key={selected.id}
          item={selected}
          who={personLabel(selected.to, roleForRequest(selected.type))}
          deal={dealName(names, selected.deal)}
          now={now}
          session={Object.hasOwn(answers, selected.id) ? answers[selected.id] : undefined}
          onRefresh={onRefresh}
        />
      )}
    </div>
  )
}

export function Inbox() {
  const now = useClockStore((s) => s.now)
  const answers = useAnswersStore((s) => s.answers)
  const q = useInbox()
  const deals = useDeals()
  const names = useMemo(() => new Map((deals.data ?? []).map((d) => [d.folder, d.legal_name ?? null])), [deals.data])

  return (
    <div className="flex flex-col gap-4">
      <PageTitle>Inbox</PageTitle>
      <Caption>Answers given here are held in this session until the engine stores them.</Caption>
      {q.isPending ? (
        <LoadingState>Loading requests.</LoadingState>
      ) : q.isError ? (
        <ErrorState heading="Could not load requests." message={describeError(q.error)} onRetry={() => void q.refetch()} />
      ) : (
        <InboxScreen items={q.data} names={names} now={now} answers={answers} onRefresh={() => void q.refetch()} />
      )}
    </div>
  )
}
