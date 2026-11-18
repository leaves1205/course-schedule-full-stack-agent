<template>
  <div class="login-container">
    <div class="login-box">
      <h1 style="font-size: 28px">Intelligent System</h1>
      <div style="margin-top: 5px; margin-bottom: 30px">An agent-powered intelligent system</div>

      <el-form ref="formRef" :rules="rules" :model="form" label-width="0px" style="width: 100%">
        <el-form-item prop="username">
          <el-input
            size="large"
            v-model="form.username"
            placeholder="Please enter a username"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            type="password"
            size="large"
            v-model="form.password"
            placeholder="Please enter a password"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <div>
          <el-button
            size="large"
            type="primary"
            style="width: 100%"
            @click="login"
            :loading="loadingValue"
            >Sign in</el-button
          >
          <div style="text-align: right; margin-top: 20px">
            No account yet? Please
            <router-link style="color: var(--el-color-primary)" to="/register">Register</router-link>
          </div>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, nextTick } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'

const { saveLoginData } = useUser()

const formRef = ref()

const form = reactive({
  username: '',
  password: ''
})

const loadingValue = ref(false)

const rules = {
  username: [{ required: true, message: 'Please enter a username', trigger: 'blur' }],
  password: [{ required: true, message: 'Please enter a password', trigger: 'blur' }]
}

const login = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loadingValue.value = true
  try {
    const res = await loginApi(form)
    if (res.code === 200) {
      saveLoginData(res.data)
      ElMessage.success('Signed in successfully')
      await router.push('/manager/home')
    }
  } finally {
    loadingValue.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}
.login-box {
  width: 380px;
  border-radius: 8px;
  box-shadow: 0 8px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
  text-align: center;
  background-color: white;
}
</style>
