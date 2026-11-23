<template>
  <div class="account-page">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>Change password</span>
        </div>
      </template>
      <el-form ref="formRef" :rules="rules" :model="form" label-position="top" style="width: 100%">
        <el-form-item label="Current password" prop="oldPassword">
          <el-input
            type="password"
            show-password
            v-model="form.oldPassword"
            placeholder="Please enter your current password"
          />
        </el-form-item>
        <el-form-item label="New password" prop="newPassword">
          <el-input
            type="password"
            show-password
            v-model="form.newPassword"
            placeholder="Please enter a new password"
          />
        </el-form-item>
        <el-form-item label="Confirm password" prop="confirmPassword">
          <el-input
            type="password"
            show-password
            v-model="form.confirmPassword"
            placeholder="Please confirm the new password"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit"
            >Save changes</el-button
          >
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { updatePassword } from '@/api/user'
import router from '@/router'
import { logout } from '@/utils/auth'
import { newPasswordRule } from '@/utils/passwordRules'
import { ElMessage } from 'element-plus'
import { ref, reactive } from 'vue'

const submitting = ref(false)
const formRef = ref()
const form = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('Please confirm the password'))
  } else {
    if (value !== form.newPassword) {
      callback(new Error('The confirmation password does not match the new password'))
    } else {
      callback()
    }
  }
}

const rules = {
  oldPassword: [{ required: true, message: 'Please enter your current password', trigger: 'blur' }],
  newPassword: [
    { required: true, message: 'Please enter a new password', trigger: 'blur' },
    newPasswordRule
  ],
  confirmPassword: [
    { validator: validatePass, message: 'Please confirm the new password', trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const res = await updatePassword({
      old_password: form.oldPassword,
      new_password: form.newPassword
    })
    if (res.code === 200) {
      ElMessage.success('Password changed successfully')
      logout()
      await router.push('/login')
    }
  } finally {
    submitting.value = false
  }
}
</script>
