//  Store, retrieve and remove the authentication token and user information.
import { clearChatMemory } from './chatMemory.js'

const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'
const SESSION_KEY = 'loginSessionId'
export const AUTH_CHANGE_EVENT = 'auth:changed'

function notifyAuthChange() {
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT))
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  clearChatMemory()
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(SESSION_KEY, crypto.randomUUID())
  notifyAuthChange()
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(SESSION_KEY)
  clearChatMemory()
  notifyAuthChange()
}

export function getSessionId() {
  if (!getToken()) return null
  let sessionId = localStorage.getItem(SESSION_KEY)
  if (!sessionId) {
    // Existing signed-in users receive a scope without needing to sign in again.
    sessionId = crypto.randomUUID()
    localStorage.setItem(SESSION_KEY, sessionId)
  }
  return sessionId
}

export function getUserInfo() {
  const str = localStorage.getItem(USER_KEY)
  return str ? JSON.parse(str) : null
}

export function setUserInfo(userInfo) {
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
}

export function removeUserInfo() {
  localStorage.removeItem(USER_KEY)
}

// Sign out
export function logout() {
  removeToken()
  removeUserInfo()
}

// Authentication is shared across tabs, but chat storage belongs to each tab.
window.addEventListener('storage', (event) => {
  if (event.storageArea === localStorage && [TOKEN_KEY, SESSION_KEY, null].includes(event.key)) {
    clearChatMemory()
    notifyAuthChange()
  }
})
