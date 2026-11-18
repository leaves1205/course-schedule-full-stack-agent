<template>
  <AuthLayout title="Sign in" description="Sign in to access your courses and schedule.">
    <el-form
      ref="formRef"
      :rules="rules"
      :model="form"
      label-position="top"
      @submit.prevent="login"
    >
      <el-form-item label="Username" prop="username"
        ><el-input
          v-model="form.username"
          placeholder="Enter your username"
          autocomplete="username"
          :prefix-icon="User"
      /></el-form-item>
      <el-form-item label="Password" prop="password"
        ><el-input
          v-model="form.password"
          type="password"
          placeholder="Enter your password"
          autocomplete="current-password"
          :prefix-icon="Lock"
          show-password
      /></el-form-item>

      <el-button
        type="primary"
        native-type="submit"
        :loading="loadingValue"
        style="width: 100%; margin-top: 8px"
        >Sign in</el-button
      >
    </el-form>
    <template #switch
      >Don't have an account?<RouterLink to="/register">Create an account</RouterLink></template
    >
  </AuthLayout>
</template>

<script setup>
import AuthLayout from '@/layouts/AuthLayout.vue'
import { reactive, ref } from 'vue'
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
