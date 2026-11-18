import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { resetStorage, storageEvent } from './browserStorage.js'
import { getSessionId, getToken, logout, setToken, setUserInfo } from '../src/utils/auth.js'
import {
  clearChatMemory, createWelcomeMessage, loadChatMemory, saveChatMemory
} from '../src/utils/chatMemory.js'

beforeEach(resetStorage)

function signIn(id = 1) {
  setToken(`token-${id}`)
  setUserInfo({ id, username: `user-${id}` })
  return { sessionId: getSessionId(), userId: String(id) }
}

function conversation() {
  const history = [
    { role: 'user', content: 'What classes do I have today?' },
    { role: 'assistant', content: 'Python at A101.' }
  ]
  return { messages: [createWelcomeMessage(), ...history], history, draft: 'And tomorrow?' }
}

test('restores completed context and draft after repeated reads', () => {
  const scope = signIn()
  saveChatMemory(scope, conversation())
  const restored = loadChatMemory(scope)
  assert.deepEqual(restored.history, conversation().history)
  assert.equal(restored.draft, 'And tomorrow?')
  assert.equal(restored.messages.length, 3)
  restored.history[0].content = 'Changed in memory'
  assert.equal(loadChatMemory(scope).history[0].content, conversation().history[0].content)
})

test('logout clears chat, credentials and scope while preserving unrelated storage', () => {
  const scope = signIn()
  saveChatMemory(scope, conversation())
  sessionStorage.setItem('unrelated', 'keep')
  logout()
  assert.equal(getToken(), null)
  assert.equal(getSessionId(), null)
  assert.equal(loadChatMemory(scope), null)
  assert.equal(sessionStorage.getItem('unrelated'), 'keep')
})

test('accounts and separate logins cannot restore another session conversation', () => {
  const alice = signIn(1)
  saveChatMemory(alice, conversation())
  assert.equal(loadChatMemory({ ...alice, userId: '2' }), null)
  saveChatMemory(alice, conversation())
  const bob = signIn(2)
  assert.equal(loadChatMemory(bob), null)
  saveChatMemory(bob, conversation())
  const bobAgain = signIn(2)
  assert.notEqual(bobAgain.sessionId, bob.sessionId)
  assert.equal(loadChatMemory(bobAgain), null)
})

test('logout in another tab clears this tab conversation', () => {
  const scope = signIn()
  saveChatMemory(scope, conversation())
  localStorage.removeItem('token')
  window.dispatchEvent(storageEvent('token'))
  assert.equal(loadChatMemory(scope), null)
})

test('interrupted output stays visible but is excluded from model history', () => {
  const scope = signIn()
  const snapshot = conversation()
  snapshot.draft = ''
  snapshot.messages.push(
    { role: 'user', content: 'And tomorrow?' },
    { role: 'assistant', content: 'Partial answer', pending: true, status: 'Generating an answer' }
  )
  saveChatMemory(scope, snapshot)
  const restored = loadChatMemory(scope)
  assert.deepEqual(restored.history, conversation().history)
  assert.equal(restored.draft, 'And tomorrow?')
  assert.equal(restored.messages.at(-1).content, 'Partial answer')
  assert.equal(restored.messages.at(-1).pending, false)
  assert.match(restored.messages.at(-1).status, /interrupted/)
})

test('invalid and incomplete cached history is ignored', () => {
  const scope = signIn()
  sessionStorage.setItem('campusChatMemory', '{broken JSON')
  assert.equal(loadChatMemory(scope), null)
  saveChatMemory(scope, { ...conversation(), history: [{ role: 'system', content: 'untrusted' }] })
  assert.equal(loadChatMemory(scope), null)
  saveChatMemory(scope, { ...conversation(), history: [{ role: 'user', content: 'Incomplete' }] })
  assert.equal(loadChatMemory(scope), null)
})

test('existing authenticated users receive a stable session scope', () => {
  localStorage.setItem('token', 'existing-token')
  const sessionId = getSessionId()
  assert.ok(sessionId)
  assert.equal(getSessionId(), sessionId)
})

test('unavailable storage does not throw or interrupt chat or logout', () => {
  const scope = signIn()
  sessionStorage.setItem = () => { throw new Error('Quota exceeded') }
  assert.doesNotThrow(() => saveChatMemory(scope, conversation()))
  sessionStorage.getItem = () => { throw new Error('Storage unavailable') }
  sessionStorage.removeItem = () => { throw new Error('Storage unavailable') }
  assert.equal(loadChatMemory(scope), null)
  assert.doesNotThrow(clearChatMemory)
  assert.doesNotThrow(logout)
})
