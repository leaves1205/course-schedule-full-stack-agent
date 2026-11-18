<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">Conversation</div>
      </template>

      <div
        ref="messageBox"
        class="messages"
        aria-live="polite"
        style="
          height: clamp(280px, calc(100dvh - 340px), 620px);
          overflow-y: auto;
          padding: 8px 4px;
          background-color: #f7f9fc;
          border-radius: 6px;
        "
      >
        <div
          v-for="(item, index) in messages"
          :key="index"
          :style="{
            display: 'flex',
            justifyContent: item.role === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: '12px'
          }"
        >
          <div
            :style="{
              maxWidth: 'min(85%, 760px)',
              padding: '10px 12px',
              borderRadius: '6px',
              backgroundColor: item.role === 'user' ? 'var(--el-color-primary)' : '#fff',
              color: item.role === 'user' ? '#fff' : '#333',
              lineHeight: '1.6',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.06)'
            }"
          >
            <!-- Current activity, such as [Querying my schedule...]. -->
            <div
              v-if="item.role === 'assistant' && item.status"
              style="margin-bottom: 6px; font-size: 12px; color: #909399"
            >
              {{ item.status }}
            </div>
            <!-- Activity from this turn; display only, do not send it back to the backend. -->
            <div
              v-if="item.role === 'assistant' && item.steps?.length"
              style="margin-bottom: 8px; font-size: 12px; color: #909399; line-height: 1.5"
            >
              <div v-for="(step, i) in item.steps" :key="i">· {{ step }}</div>
            </div>
            <div
              v-if="item.role === 'user' && item.content"
              style="white-space: pre-wrap; word-break: break-word"
            >
              {{ item.content }}
            </div>
            <div
              v-else-if="item.content"
              class="chat-md"
              v-html="parseMarkdown(item.content)"
            ></div>
          </div>
        </div>
      </div>
      <!-- Input field -->
      <div style="margin-top: 12px; display: flex; gap: 8px; align-items: flex-end">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          aria-label="Enter a question"
          placeholder="For example: What classes do I have tomorrow?"
          @keydown.enter.exact.prevent="send"
          @keydown.enter.shift.stop
        ></el-input>
        <el-button type="primary" :loading="sending" @click="send">Send</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { streamChat } from '@/api/chat'
import { AUTH_CHANGE_EVENT, getSessionId, getToken, getUserInfo } from '@/utils/auth'
import { clearChatMemory, createWelcomeMessage, loadChatMemory, saveChatMemory } from '@/utils/chatMemory'

marked.setOptions({ gfm: true, breaks: true })

const scope = { sessionId: getSessionId(), userId: String(getUserInfo()?.id || '') }
const restored = loadChatMemory(scope)
const question = ref(restored?.draft || '')
const messages = ref(restored?.messages || [createWelcomeMessage()])
const history = ref(restored?.history || [])
const sending = ref(false)
const messageBox = ref(null)
const toolLabels = { get_my_schedules: 'Query my schedule' }
let activeController = null
let disposed = false

function isCurrentSession() {
  return Boolean(getToken()) && getSessionId() === scope.sessionId &&
    String(getUserInfo()?.id || '') === scope.userId
}

function persistConversation() {
  if (disposed || !isCurrentSession()) return
  saveChatMemory(scope, { messages: messages.value, history: history.value, draft: question.value })
}

function handleAuthChange() {
  if (isCurrentSession()) return
  activeController?.abort()
  clearChatMemory()
  messages.value = [createWelcomeMessage()]
  history.value = []
  question.value = ''
  sending.value = false
}

watch([messages, history, question], persistConversation, { deep: true })
onMounted(() => {
  window.addEventListener(AUTH_CHANGE_EVENT, handleAuthChange)
  scrollToBottom()
})
onUnmounted(() => {
  persistConversation()
  disposed = true
  activeController?.abort()
  window.removeEventListener(AUTH_CHANGE_EVENT, handleAuthChange)
})

function parseMarkdown(text) {
  return DOMPurify.sanitize(marked.parse(text || ''), { USE_PROFILES: { html: true } })
}

async function scrollToBottom() {
  await nextTick()
  messageBox.value?.scrollTo({ top: messageBox.value.scrollHeight })
}

async function send() {
  const text = question.value.trim()
  // Send one question at a time on this page; do not submit blank input.
  if (sending.value || !text || !isCurrentSession()) return
  const controller = new AbortController()
  activeController = controller
  const previousHistory = history.value.map((item) => ({ ...item }))
  messages.value.push({ role: 'user', content: text })
  messages.value.push({ role: 'assistant', content: '', status: 'Connecting', steps: [], pending: true })
  const reply = messages.value[messages.value.length - 1]
  question.value = ''
  sending.value = true
  persistConversation()
  scrollToBottom()

  try {
    await streamChat({ question: text, history: previousHistory }, (event) => {
      if (disposed || controller.signal.aborted || !isCurrentSession()) return
      const label = toolLabels[event.name] || event.name
      // Display status separately from the answer and append text chunks as they arrive.
      if (event.type === 'status') {
        reply.status = event.message
      } else if (event.type === 'token') {
        reply.content += event.content
        reply.status = ''
        // Append readable activity text only; exclude it from the next conversation history.
      } else if (event.type === 'tool_start') {
        reply.status = `Running: ${label}`
        reply.steps.push(`Started: ${label}`)
      } else if (event.type === 'tool_end') {
        reply.status = `${label} returned`
        reply.steps.push(`Returned: ${label}`)
        // Use done to finalize the answer; add only successful exchanges to history.
      } else if (event.type === 'done') {
        reply.content = event.answer
        reply.status = ''
        reply.pending = false
        history.value.push(
          { role: 'user', content: text },
          { role: 'assistant', content: event.answer }
        )
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
      scrollToBottom()
    }, { signal: controller.signal })
  } catch (error) {
    if (disposed || controller.signal.aborted || !isCurrentSession()) return
    reply.pending = false
    reply.status = `Incomplete: ${error.message}`
    question.value = text
    ElMessage.error(error.message)
  } finally {
    if (activeController === controller) activeController = null
    if (!disposed && isCurrentSession()) {
      reply.pending = false
      sending.value = false
      persistConversation()
      scrollToBottom()
    }
  }
}
</script>

<style scoped>
.chat-md :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
  display: table;
}
.chat-md :deep(thead),
.chat-md :deep(tbody) {
  display: table-row-group;
}
.chat-md :deep(tr) {
  display: table-row;
}
.chat-md :deep(th),
.chat-md :deep(td) {
  display: table-cell;
  border: 1px solid #dcdfe6;
  padding: 6px 10px;
  text-align: left;
  vertical-align: top;
  word-break: break-word;
}
.chat-md :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}
.chat-md :deep(p) {
  margin: 0.4em 0;
}
.chat-md :deep(p:first-child) {
  margin-top: 0;
}
.chat-md :deep(p:last-child) {
  margin-bottom: 0;
}
.chat-md :deep(ul),
.chat-md :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.4em;
}
</style>
