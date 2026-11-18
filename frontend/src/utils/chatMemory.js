const CHAT_MEMORY_KEY = 'campusChatMemory'
const MEMORY_VERSION = 1

export function createWelcomeMessage() {
  return {
    role: 'assistant',
    content: 'Hello, I am your campus course assistant. Ask about your schedule, for example: What classes do I have tomorrow?',
    status: '',
    steps: [],
    pending: false
  }
}

function isMessage(message) {
  return message && ['user', 'assistant'].includes(message.role) && typeof message.content === 'string'
}

function normalizeSnapshot(snapshot) {
  if (!snapshot || !Array.isArray(snapshot.messages) || !snapshot.messages.every(isMessage)) return null
  if (!Array.isArray(snapshot.history) || snapshot.history.length % 2 !== 0) return null
  if (!snapshot.history.every((message, index) =>
    isMessage(message) && message.role === (index % 2 === 0 ? 'user' : 'assistant')
  )) return null
  if (typeof snapshot.draft !== 'string') return null

  return {
    messages: snapshot.messages.map((message) => ({
      role: message.role,
      content: message.content,
      status: typeof message.status === 'string' ? message.status : '',
      steps: Array.isArray(message.steps) ? message.steps.filter((step) => typeof step === 'string') : [],
      pending: message.role === 'assistant' && message.pending === true
    })),
    history: snapshot.history.map(({ role, content }) => ({ role, content })),
    draft: snapshot.draft
  }
}

export function clearChatMemory() {
  try {
    sessionStorage.removeItem(CHAT_MEMORY_KEY)
  } catch {
    // Chat remains usable when browser storage is unavailable.
  }
}

export function saveChatMemory(scope, snapshot) {
  if (!scope?.sessionId || !scope?.userId) return
  const normalized = normalizeSnapshot(snapshot)
  if (!normalized) return
  try {
    sessionStorage.setItem(CHAT_MEMORY_KEY, JSON.stringify({
      version: MEMORY_VERSION,
      sessionId: scope.sessionId,
      userId: String(scope.userId),
      ...normalized
    }))
  } catch {
    // Storage limits must not interrupt a live conversation.
  }
}

export function loadChatMemory(scope) {
  if (!scope?.sessionId || !scope?.userId) return null
  try {
    const cached = JSON.parse(sessionStorage.getItem(CHAT_MEMORY_KEY) || 'null')
    if (!cached) return null
    const normalized = normalizeSnapshot(cached)
    if (
      cached.version !== MEMORY_VERSION || cached.sessionId !== scope.sessionId ||
      cached.userId !== String(scope.userId) || !normalized
    ) {
      clearChatMemory()
      return null
    }

    if (normalized.messages.some((message) => message.pending)) {
      if (!normalized.draft) {
        normalized.draft = normalized.messages.findLast((message) => message.role === 'user')?.content || ''
      }
      for (const message of normalized.messages) {
        if (message.pending) {
          message.pending = false
          message.status = 'Incomplete: This reply was interrupted. Please send your question again.'
        }
      }
    }
    return normalized
  } catch {
    clearChatMemory()
    return null
  }
}
