<template>
  <AuthLayout title="Create an account" description="Register to access your course workspace.">
    <el-form
      ref="formRef"
      :rules="rules"
      :model="form"
      label-position="top"
      @submit.prevent="register"
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
          autocomplete="new-password"
          :prefix-icon="Lock"
          show-password
      /></el-form-item>
      <el-form-item label="Confirm password" prop="confirmPassword"
        ><el-input
          v-model="form.confirmPassword"
          type="password"
          placeholder="Confirm your password"
          autocomplete="new-password"
          show-password
          :prefix-icon="Lock"
      /></el-form-item>
      <el-button
        type="primary"
        native-type="submit"
        :loading="loadingValue"
        style="width: 100%; margin-top: 8px"
        >Create account</el-button
      >
    </el-form>
    <template #switch
      >Already have an account?<RouterLink to="/login">Sign in</RouterLink></template
    >
  </AuthLayout>
</template>

<script setup>
import AuthLayout from '@/layouts/AuthLayout.vue'
import { reactive, ref } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { registerApi } from '@/api/auth'
import { newPasswordRule, usernameRule } from '@/utils/passwordRules'
import router from '@/router'

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const loadingValue = ref(false)

const formRef = ref()

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Please confirm the password'))
  } else {
    if (value !== form.password) {
      callback(new Error('The passwords do not match'))
    } else {
      callback()
    }
  }
}
const rules = {
  username: [{ required: true, message: 'Please enter a username', trigger: 'blur' }, usernameRule],
  password: [{ required: true, message: 'Please enter a password', trigger: 'blur' }, newPasswordRule],
  confirmPassword: [{ validator: validatePass, trigger: 'blur' }]
}

const register = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loadingValue.value = true
  try {
    const res = await registerApi(form)
    if (res.code === 200) {
      ElMessage.success('Registered successfully')
      await router.push('/login')
    }
  } finally {
    loadingValue.value = false
  }
}
</script>
