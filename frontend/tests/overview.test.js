import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { parse, compileScript } from '@vue/compiler-sfc'
import { createRenderer, ref } from 'vue'

async function loadComponent(path) {
  const { descriptor } = parse(readFileSync(new URL(path, import.meta.url), 'utf8'))
  let script = compileScript(descriptor, { id: path }).content
  script = script
    .replace(/import \{ ([^}]+) \} from ['"]@\/api\/[^'"]+['"];?/g, (_, names) =>
      names
        .split(',')
        .map((name) => name.trim())
        .map((name) => `const ${name} = (...args) => globalThis.overviewApi.${name}(...args)`)
        .join('\n')
    )
    .replace(
      /import \{ useUser \} from ['"]@\/utils\/user['"];?/,
      'const useUser = () => ({ userInfo: globalThis.overviewUser })'
    )
    .replace(/from (['"])([^'"]+)\1/g, (_, quote, name) => `from '${import.meta.resolve(name)}'`)
  const { default: component } = await import(
    `data:text/javascript;base64,${Buffer.from(script).toString('base64')}`
  )
  component.render = () => null
  return component
}
const Home = await loadComponent('../src/views/Home.vue')
const Sidebar = await loadComponent('../src/layouts/AppSidebar.vue')
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
const success = (data) => ({ code: 200, data })
let calls
beforeEach(() => {
  calls = []
  globalThis.overviewUser = ref({ name: 'Alice', role: 'student' })
  globalThis.overviewApi = {
    listSchedulesApi: async (params) => {
      calls.push(['schedules', params])
      return success(
        params.date
          ? { list: [{ id: 7, course_name: 'Math', period: '1-2' }], total: 1 }
          : { list: [], total: 8 }
      )
    },
    listStudyPlans: async () => {
      calls.push(['plans'])
      return success({ list: [], total: 3 })
    },
    listCoursesApi: async () => {
      calls.push(['courses'])
      return success([{ id: 1 }, { id: 2 }])
    },
    getUserPageList: async () => {
      calls.push(['users'])
      return success({ list: [], total: 12 })
    }
  }
})
function mount(t, component) {
  const app = renderer.createApp(component)
  const instance = app.mount({})
  t.after(() => app.unmount())
  return instance.$.setupState
}
const settle = () => new Promise((resolve) => setImmediate(resolve))

test('student overview uses own-account APIs and local calendar date', async (t) => {
  const page = mount(t, Home)
  await settle()
  assert.equal(page.loading, false)
  assert.deepEqual(
    page.stats.map((stat) => stat.value),
    [1, 8, 3]
  )
  assert.deepEqual(
    calls.map(([name]) => name),
    ['schedules', 'schedules', 'plans']
  )
  const date = page.today
  assert.equal(
    calls[0][1].date,
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  )
  assert.equal(page.schedulePath, '/manager/schedule')
  assert.equal(page.schedules[0].course_name, 'Math')
})

test('admin overview counts courses and accounts and links to management', async (t) => {
  globalThis.overviewUser.value.role = 'admin'
  const page = mount(t, Home)
  await settle()
  assert.deepEqual(
    page.stats.map((stat) => stat.value),
    [1, 2, 12]
  )
  assert.deepEqual(
    calls.map(([name]) => name),
    ['schedules', 'courses', 'users']
  )
  assert.equal(page.schedulePath, '/manager/scheduleManage')
  assert.equal(page.stats[2].label, 'Accounts')
})

test('partial failures remain unavailable instead of becoming zero and can retry', async (t) => {
  globalThis.overviewApi.listSchedulesApi = async () => {
    throw new Error('Offline')
  }
  const page = mount(t, Home)
  await settle()
  assert.equal(page.loading, false)
  assert.equal(page.scheduleError, true)
  assert.deepEqual(
    page.stats.map((stat) => stat.value),
    [null, null, 3]
  )
  globalThis.overviewApi.listSchedulesApi = async () => success({ list: [], total: 0 })
  await page.loadOverview()
  assert.equal(page.scheduleError, false)
  assert.deepEqual(
    page.stats.map((stat) => stat.value),
    [0, 0, 3]
  )
})

test('sidebar separates student and administrator navigation', (t) => {
  const page = mount(t, Sidebar)
  assert.deepEqual(
    page.workspaceLinks.map((link) => link.to),
    ['/manager/home', '/manager/schedule', '/manager/study-plan', '/manager/chat']
  )
  globalThis.overviewUser.value.role = 'admin'
  assert.deepEqual(
    page.workspaceLinks.map((link) => link.to),
    [
      '/manager/home',
      '/manager/course',
      '/manager/semesters',
      '/manager/scheduleManage',
      '/manager/user',
      '/manager/documents',
      '/manager/chat'
    ]
  )
})

test('recent plans display saved content and dates with a three-item limit', async (t) => {
  let request
  globalThis.overviewApi.listStudyPlans = async (params) => {
    request = params
    return success({
      total: 4,
      list: [1, 2, 3, 4].map((id) => ({
        id,
        content: `# Review chapter ${id}`,
        create_time: '2026-11-18T11:05:37'
      }))
    })
  }
  const page = mount(t, Home)
  await settle()
  assert.equal(request.page_size, 3)
  assert.equal(page.tertiaryTotal, 4)
  assert.equal(page.recentUnavailable, false)
  assert.deepEqual(
    page.recentItems.map((item) => item.id),
    [1, 2, 3]
  )
  assert.equal(page.previewText(page.recentItems[0].content), 'Review chapter 1')
  assert.equal(page.formatDate(page.recentItems[0].create_time), '2026-11-18 11:05')
})

test('failed plan requests show unavailable data and preserve schedule results', async (t) => {
  globalThis.overviewApi.listStudyPlans = async () => {
    throw new Error('Offline')
  }
  const page = mount(t, Home)
  await settle()
  assert.equal(page.recentUnavailable, true)
  assert.equal(page.tertiaryTotal, null)
  assert.equal(page.scheduleTotal, 1)
  assert.deepEqual(page.recentItems, [])
})
