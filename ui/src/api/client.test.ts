import { afterEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { ApiError, describeError, getAlerts, getDeal, getDeals, getInbox, postAdvance, postReplay, postReply, setApiBase } from './client.ts'

interface Call {
  url: string
  init: RequestInit | undefined
}

const realFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = realFetch
  setApiBase('')
})

function stub(respond: (call: Call) => Response | Promise<Response>): Call[] {
  const calls: Call[] = []
  globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
    const call = { url: String(url), init }
    calls.push(call)
    return respond(call)
  }) as typeof fetch
  return calls
}

const json = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

test('getDeal encodes folder names with apostrophes and ampersands', async () => {
  const calls = stub(() => json({ folder: 'x' }))
  await getDeal('Bayou Bistro & Grill')
  await getDeal("Mama Rosa's Kitchen")
  assert.equal(calls[0].url, `/api/deals/${encodeURIComponent('Bayou Bistro & Grill')}`)
  assert.equal(calls[0].url, '/api/deals/Bayou%20Bistro%20%26%20Grill')
  assert.equal(calls[1].url, `/api/deals/${encodeURIComponent("Mama Rosa's Kitchen")}`)
})

test('postAdvance sends POST, JSON content-type and a body with the single key to', async () => {
  const calls = stub(() => json({ now: 'a', start: 'b', end: 'c' }))
  await postAdvance('2026-11-03T15:05-06:00')
  assert.equal(calls[0].url, '/api/clock/advance')
  assert.equal(calls[0].init?.method, 'POST')
  const headers = new Headers(calls[0].init?.headers)
  assert.equal(headers.get('content-type'), 'application/json')
  const body = JSON.parse(String(calls[0].init?.body))
  assert.deepEqual(body, { to: '2026-11-03T15:05-06:00' })
  assert.deepEqual(Object.keys(body), ['to'])
})

test('postReplay sends POST with the empty object', async () => {
  const calls = stub(() => json({ now: 'a', start: 'b', end: 'c' }))
  await postReplay()
  assert.equal(calls[0].url, '/api/clock/replay')
  assert.equal(calls[0].init?.method, 'POST')
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {})
})

async function errorFrom(p: Promise<unknown>): Promise<unknown> {
  try {
    await p
  } catch (e) {
    return e
  }
  throw new Error('expected a rejection')
}

test('describeError: 503 maps to the engine-not-connected text', async () => {
  stub(() => json({ detail: 'engine not wired yet' }, 503))
  assert.equal(describeError(await errorFrom(getDeals())), 'The engine is not connected.')
})

test('describeError: a 422 detail string is shown exactly', async () => {
  stub(() => json({ detail: 'option must be one of: approve, decline' }, 422))
  const e = await errorFrom(postAdvance('2026-11-03T15:05-06:00'))
  assert.ok(e instanceof ApiError)
  assert.equal(describeError(e), 'option must be one of: approve, decline')
})

test('describeError: a thrown network TypeError is "not reachable"', async () => {
  stub(() => {
    throw new TypeError('fetch failed')
  })
  assert.equal(
    describeError(await errorFrom(getDeals())),
    'The API is not reachable. Start the mock server on port 8000.',
  )
})

test('describeError: a non-JSON 500 body is a fixed HTTP message, never the raw body', async () => {
  stub(() => new Response('<html>Traceback boom</html>', { status: 500 }))
  assert.equal(describeError(await errorFrom(getDeals())), 'Request failed (HTTP 500)')
})

test('postReply sends POST to the encoded item id with a body that is exactly the single key option', async () => {
  const calls = stub(() => json({ id: 'inbox-001' }))
  await postReply('inbox-001', 'approve')
  assert.equal(calls[0].url, '/api/inbox/inbox-001/reply')
  assert.equal(calls[0].init?.method, 'POST')
  assert.equal(new Headers(calls[0].init?.headers).get('content-type'), 'application/json')
  const body = JSON.parse(String(calls[0].init?.body))
  assert.deepEqual(body, { option: 'approve' })
  assert.deepEqual(Object.keys(body), ['option'])
})

test('postReply sends a trimmed note, omits an empty or whitespace note and caps a note at 500 characters', async () => {
  const calls = stub(() => json({ id: 'x' }))
  await postReply('inbox-001', 'approve', '  call me  ')
  await postReply('inbox-001', 'approve', '')
  await postReply('inbox-001', 'approve', '   \n ')
  await postReply('inbox-001', 'approve', 'x'.repeat(600))
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { option: 'approve', note: 'call me' })
  assert.deepEqual(JSON.parse(String(calls[1].init?.body)), { option: 'approve' })
  assert.deepEqual(JSON.parse(String(calls[2].init?.body)), { option: 'approve' })
  const capped = JSON.parse(String(calls[3].init?.body))
  assert.deepEqual(Object.keys(capped).sort(), ['note', 'option'])
  assert.equal(capped.note.length, 500)
})

test('postReply encodes the item id with encodeURIComponent', async () => {
  const calls = stub(() => json({}))
  await postReply('a/b c?d', 'approve')
  assert.equal(calls[0].url, `/api/inbox/${encodeURIComponent('a/b c?d')}/reply`)
  assert.equal(calls[0].url, '/api/inbox/a%2Fb%20c%3Fd/reply')
})

test('postReply 409 keeps the status for the caller; the detail text is available too', async () => {
  stub(() => json({ detail: 'already answered' }, 409))
  const e = await errorFrom(postReply('inbox-001', 'approve'))
  assert.ok(e instanceof ApiError)
  assert.equal(e.status, 409)
  assert.equal(describeError(e), 'already answered')
})

test('getInbox and getAlerts are plain GETs', async () => {
  const calls = stub(() => json([]))
  await getInbox()
  await getAlerts()
  assert.equal(calls[0].url, '/api/inbox')
  assert.equal(calls[1].url, '/api/alerts')
  assert.equal(calls[0].init, undefined)
  assert.equal(calls[1].init, undefined)
})
