// For use in page setup functions only.
import { ref } from 'vue'
import { getUserInfo, setToken, setUserInfo } from './auth'

const userInfo = ref(getUserInfo()) // Reactive state that can be updated whenever user information changes.

export function useUser() {
  function saveLoginData(data) {
    setToken(data.token)
    setUserInfo(data.user)
    userInfo.value = data.user
  }

  function updateUser(user) {
    setUserInfo(user)
    userInfo.value = user
  }

  function reloadUser() {
    userInfo.value = getUserInfo()
  }

  return {
    userInfo,
    saveLoginData,
    updateUser,
    reloadUser
  }
}
