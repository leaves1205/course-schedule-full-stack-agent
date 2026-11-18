import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import { createRenderer, nextTick } from 'vue'
import { resetStorage, storageEvent } from './browserStorage.js'
import { logout, setToken, setUserInfo } from '../src/utils/auth.js'

const source = readFileSync(new URL('../src/views/Chat.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
let script = compileScript(descriptor, { id: 'chat-session-test' }).content
script = script
  .replace(/import \{ streamChat \} from ['"]@\/api\/chat['"];?/, 'const streamChat = (...args) => globalThis.chatStream(...args)')
  .replace(/import \{ ElMessage \} from ['"]element-plus['"];?/, 'const ElMessage = { error: (...args) => globalThis.chatErrors.push(args) }')
  .replace(/from (['"])([^'"]+)\1/g, (_, quote, name) => {
    const url = name.startsWith('@/')
      ? new URL(`../src/${name.slice(2)}.js`, import.meta.url).href
      : import.meta.resolve(name)
    return `from '${url}'`
  })
const { default: Chat } = await import(`data:text/javascript;base64,${Buffer.from(script).toString('base64')}`)
Chat.render = () => null

const renderer = createRenderer({
  createElement: () => ({}),
  createText: () => ({}),
  createComment: () => ({}),
  setText() {},
  setElementText() {},
  parentNode: () => null,
  nextSibling: () => null,
  insert() {},
  remove() {},
  patchProp() {}
})

beforeEach(() => {
  resetStorage()
  globalThis.chatErrors = []
  setToken('alice-token')
  setUserInfo({ id: 1, username: 'alice' })
})

function mount(t) {
  const app = renderer.createApp(Chat)
  const instance = app.mount({})
  let mounted = true
  const unmount = () => { if (mounted) { mounted = false; app.unmount() } }
  t.after(unmount)
  return { state: instance.$.setupState, unmount }
}

function holdReply(onEvent) {
  globalThis.chatStream = async (body, receive, { signal }) => {
    onEvent?.(body, receive, signal)
    return new Promise((resolve, reject) => {
      signal.addEventListener('abort', () => {
        receive({ type: 'token', content: 'LATE DATA MUST BE IGNORED' })
        reject(new DOMException('Aborted', 'AbortError'))
      }, { once: true })
    })
  }
}

test('completed conversation and draft survive remount and feed the next request', async (t) => {
  const requests = []
  globalThis.chatStream = async (body, receive) => {
    requests.push(body)
    receive({ type: 'token', content: 'Python' })
    receive({ type: 'done', answer: 'Python at A101.', tools_used: [] })
  }
  const first = mount(t)
  first.state.question = 'What classes do I have today?'
  await first.state.send()
  first.state.question = 'And tomorrow?'
  await nextTick()
  first.unmount()

  const second = mount(t)
  assert.equal(second.state.messages.length, 3)
  assert.equal(second.state.question, 'And tomorrow?')
  assert.equal(second.state.history.length, 2)
  await second.state.send()
  assert.deepEqual(requests[1].history, requests[0].history.concat([
    { role: 'user', content: 'What classes do I have today?' },
    { role: 'assistant', content: 'Python at A101.' }
  ]))
})

test('logout aborts a live reply and prevents late events from restoring memory', async (t) => {
  let signal
  holdReply((body, receive, activeSignal) => { signal = activeSignal })
  const page = mount(t)
  page.state.question = 'Show my schedule'
  const sending = page.state.send()
  await nextTick()
  logout()
  await sending
  assert.equal(signal.aborted, true)
  assert.equal(page.state.messages.length, 1)
  assert.deepEqual(page.state.history, [])
  assert.equal(sessionStorage.length, 0)
  assert.deepEqual(globalThis.chatErrors, [])
  page.unmount()

  setToken('alice-new-token')
  setUserInfo({ id: 1, username: 'alice' })
  const nextLogin = mount(t)
  assert.equal(nextLogin.state.messages.length, 1)
  assert.deepEqual(nextLogin.state.history, [])
})

test('leaving during a reply restores the question without adding partial model context', async (t) => {
  holdReply((body, receive) => { receive({ type: 'token', content: 'Partial answer' }) })
  const page = mount(t)
  page.state.question = 'Show my schedule'
  const sending = page.state.send()
  await nextTick()
  page.unmount()
  await sending

  const restored = mount(t)
  assert.equal(restored.state.question, 'Show my schedule')
  assert.equal(restored.state.messages.at(-1).content, 'Partial answer')
  assert.match(restored.state.messages.at(-1).status, /interrupted/)
  assert.deepEqual(restored.state.history, [])
  assert.deepEqual(globalThis.chatErrors, [])
})

test('logout from another tab clears the visible conversation and persisted history', async (t) => {
  globalThis.chatStream = async (body, receive) => {
    receive({ type: 'done', answer: 'Python at A101.', tools_used: [] })
  }
  const page = mount(t)
  page.state.question = 'Show my schedule'
  await page.state.send()
  localStorage.removeItem('token')
  window.dispatchEvent(storageEvent('token'))
  await nextTick()
  assert.equal(page.state.messages.length, 1)
  assert.deepEqual(page.state.history, [])
  assert.equal(sessionStorage.length, 0)
})
