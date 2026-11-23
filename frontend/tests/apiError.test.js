import assert from 'node:assert/strict'
import test from 'node:test'
import { settleFailedRequest } from '../src/utils/apiError.js'

function run(err) {
  const calls = { messages: [], expired: 0 }
  const outcome = settleFailedRequest(err, {
    notify: (message) => calls.messages.push(message),
    onSessionExpired: () => (calls.expired += 1)
  })
  return { outcome, calls }
}

const failure = (status, data) => ({ response: { status, data } })

test('business errors resolve with the envelope so views can read the code and data', () => {
  const body = { code: 409, message: 'Found 2 period conflicts.', data: { conflicts: [{ date: '2026-08-03' }] } }
  const { outcome, calls } = run(failure(409, body))
  assert.deepEqual(outcome, { resolve: body })
  assert.deepEqual(calls.messages, ['Found 2 period conflicts.'])
  assert.equal(calls.expired, 0)
})

test('validation and rate limit failures resolve with their envelope and tell the user', () => {
  for (const [status, message] of [
    [422, 'Password must contain at least one letter and one digit.'],
    [429, 'Too many requests. Please wait a moment and try again.']
  ]) {
    const body = { code: status, message }
    const { outcome, calls } = run(failure(status, body))
    assert.deepEqual(outcome, { resolve: body })
    assert.deepEqual(calls.messages, [message])
  }
})

test('an expired session signs out and rejects instead of continuing', () => {
  const err = failure(401, { code: 401, message: 'Invalid login credentials.' })
  const { outcome, calls } = run(err)
  assert.deepEqual(outcome, { reject: err })
  assert.deepEqual(calls.messages, ['Your session has expired. Please sign in again.'])
  assert.equal(calls.expired, 1)
})

test('server errors without an envelope reject with a generic message', () => {
  const err = failure(502, '<html>Bad gateway</html>')
  const { outcome, calls } = run(err)
  assert.deepEqual(outcome, { reject: err })
  assert.deepEqual(calls.messages, ['Request failed'])
  assert.equal(calls.expired, 0)
})

test('network failures reject and name the likely cause', () => {
  const err = new Error('Network Error')
  const { outcome, calls } = run(err)
  assert.deepEqual(outcome, { reject: err })
  assert.deepEqual(calls.messages, ['Network error. Check the backend service.'])
})
