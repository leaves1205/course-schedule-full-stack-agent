import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import { createRenderer } from 'vue'

const source = readFileSync(
  new URL('../src/components/GenerateScheduleDialog.vue', import.meta.url),
  'utf8'
)
const { descriptor } = parse(source)
let script = compileScript(descriptor, { id: 'semester-generation-test' }).content
script = script
  .replace(
    /import \{ generateSchedulesApi \} from ['"]@\/api\/schedule['"];?/,
    'const generateSchedulesApi = (...args) => globalThis.generateScheduleMock(...args)'
  )
  .replace(
    /import \{ ElMessage \} from ['"]element-plus['"];?/,
    'const ElMessage = { success: value => globalThis.generationMessages.push(value), warning: value => globalThis.generationMessages.push(value) }'
  )
  .replace(/from (['"])([^'"]+)\1/g, (_, quote, name) => `from '${import.meta.resolve(name)}'`)
const { default: Dialog } = await import(
  `data:text/javascript;base64,${Buffer.from(script).toString('base64')}`
)
Dialog.render = () => null
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
  globalThis.generationMessages = []
})
function mount(t) {
  const events = []
  const app = renderer.createApp(Dialog, {
    modelValue: true,
    semesters: [{ id: 1, name: 'Semester 2', first_monday: '2026-08-03', total_weeks: 16 }],
    semesterId: 1,
    userId: 2,
    students: [],
    courses: [],
    'onUpdate:modelValue': (value) => events.push(['visible', value]),
    onGenerated: (value) => events.push(['generated', value])
  })
  const instance = app.mount({})
  t.after(() => app.unmount())
  const state = instance.$.setupState
  state.formRef = { validate: async () => true }
  state.form.course_id = 3
  state.form.meetings[0].location = 'A201'
  state.addMeeting()
  Object.assign(state.form.meetings[1], { start_period: 3, end_period: 4, location: 'A201' })
  return { state, events }
}

test('weekly form previews 32 classes and submits all rows together', async (t) => {
  let payload
  globalThis.generateScheduleMock = async (body) => {
    payload = body
    return { code: 200, data: { created_count: 32, preserved_count: 0 } }
  }
  const { state, events } = mount(t)
  assert.equal(state.sessionCount, 32)
  assert.match(state.dateRange, /2026/)
  await state.generate()
  assert.deepEqual(payload, {
    semester_id: 1,
    user_id: 2,
    course_id: 3,
    start_week: 1,
    end_week: 16,
    meetings: [
      { weekday: 1, start_period: 1, end_period: 2, location: 'A201' },
      { weekday: 4, start_period: 3, end_period: 4, location: 'A201' }
    ]
  })
  assert.deepEqual(events, [
    ['generated', { semesterId: 1, userId: 2 }],
    ['visible', false]
  ])
})

test('conflicts keep the form open and display structured details', async (t) => {
  const conflicts = [{ date: '2026-08-03', requested_period: '1-2', existing_period: '2-3' }]
  globalThis.generateScheduleMock = async () => ({
    code: 409,
    data: { conflicts, conflict_count: 1 }
  })
  const { state, events } = mount(t)
  await state.generate()
  assert.equal(state.saving, false)
  assert.deepEqual(state.conflicts, conflicts)
  assert.equal(state.conflictCount, 1)
  assert.deepEqual(events, [])
})

test('pending submission blocks duplicate requests and dismissal', async (t) => {
  let finish
  let calls = 0
  globalThis.generateScheduleMock = () => {
    calls++
    return new Promise((resolve) => {
      finish = resolve
    })
  }
  const { state, events } = mount(t)
  const pending = state.generate()
  await new Promise((resolve) => setImmediate(resolve))
  await state.generate()
  state.close()
  assert.equal(calls, 1)
  assert.deepEqual(events, [])
  finish({ code: 200, data: { created_count: 0, preserved_count: 32 } })
  await pending
  assert.equal(state.saving, false)
  assert.match(globalThis.generationMessages[0], /preserved 32/)
})

test('invalid week or period ranges never call generation', async (t) => {
  let calls = 0
  globalThis.generateScheduleMock = async () => {
    calls++
  }
  const { state } = mount(t)
  state.form.end_week = 17
  await state.generate()
  state.form.end_week = 16
  state.form.meetings[0].end_period = 0
  await state.generate()
  assert.equal(calls, 0)
  assert.equal(globalThis.generationMessages.length, 2)
})
