<template>
  <div class="account-page">
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>Profile</span>
        </div>
      </template>
      <el-form
        ref="formRef"
        :rules="rules"
        :model="form"
        label-position="top"
        style="width: 100%"
        v-loading="loading"
      >
        <el-form-item label="Avatar">
          <el-upload
            class="avatar-uploader"
            :http-request="handleFileUpload"
            :show-file-list="false"
            accept="image/jpeg,image/png,image/gif,image/webp"
            :before-upload="beforeAvatarUpload"
          >
            <img v-if="form.avatar" :src="form.avatar" class="avatar" />
            <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
          </el-upload>
        </el-form-item>
        <el-form-item label="Username">
          <el-input disabled v-model="form.username" placeholder="Please enter a username" />
        </el-form-item>
        <el-form-item label="Name" prop="name">
          <el-input v-model="form.name" placeholder="Please enter a name" />
        </el-form-item>
        <el-form-item label="Role">
          <el-input disabled v-model="roleLabel" />
        </el-form-item>
        <el-form-item label="Email" prop="email">
          <el-input v-model="form.email" placeholder="Please enter an email address" />
        </el-form-item>
        <el-form-item label="Phone number" prop="phone">
          <el-input v-model="form.phone" placeholder="Please enter a phone number" />
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
import { getUserInfo, updateUserInfo } from '@/api/user'
import { uploadFileApi } from '@/api/file'
import { ref, reactive, onMounted, computed } from 'vue'
import { useUser } from '@/utils/user'
import { ElMessage } from 'element-plus'

const { updateUser } = useUser()

const loading = ref(false)
const submitting = ref(false)
const formRef = ref()
const form = reactive({
  username: '',
  name: '',
  role: '',
  email: '',
  phone: '',
  avatar: ''
})

const rules = {
  name: [{ required: true, message: 'Please enter a name', trigger: 'blur' }],
  email: [{ type: 'email', message: 'Invalid email address', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: 'Invalid phone number', trigger: 'blur' }]
}

const roleLabel = computed(() => {
  return form.role === 'admin'
    ? 'Administrator'
    : form.role === 'student'
      ? 'Student'
      : 'Unknown role'
})

const beforeAvatarUpload = (file) => {
  const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!imageTypes.includes(file.type)) {
    ElMessage.error('Only image uploads are allowed')
    return false
  }
  if (file.size / 1024 / 1024 > 2) {
    ElMessage.error('The image size must not exceed 2 MB')
    return false
  }
  return true
}

const handleFileUpload = async ({ file }) => {
  try {
    const res = await uploadFileApi(file)
    if (res.code === 200) {
      form.avatar = res.data?.url
    }
  } catch {}
}

const loadUserInfo = async () => {
  loading.value = true
  try {
    const res = await getUserInfo()
    if (res.code === 200) {
      Object.assign(form, res.data)
    }
  } finally {
    loading.value = false
  }
}

// Send a request to update user information.
const handleSubmit = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const res = await updateUserInfo(form)
    if (res.code === 200) {
      updateUser(res.data)
      ElMessage.success('Updated successfully')
    }
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadUserInfo()
})
</script>

<style scoped>
.avatar-uploader .avatar {
  width: 130px;
  height: 130px;
  display: block;
}
</style>
<style>
.avatar-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}
.avatar-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}
.el-icon.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 130px;
  height: 130px;
  text-align: center;
}
</style>
