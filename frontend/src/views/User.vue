<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">
          <span>User list</span>
        </div>
      </template>
      <div class="table-toolbar">
        <el-input
          placeholder="Search by username or name"
          aria-label="Search users"
          v-model="params.keywords"
          style="width: 280px"
          clearable
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        ></el-input>
        <el-button :icon="Search" @click="handleSearch">Search</el-button>
        <el-button class="toolbar-create" type="primary" :icon="Plus" @click="handleCreate"
          >Add user</el-button
        >
      </div>

      <el-table
        :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#333' }"
        :data="tableData"
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column prop="username" label="Username" min-width="140" show-overflow-tooltip />
        <el-table-column prop="name" label="Name" min-width="140" show-overflow-tooltip />
        <el-table-column prop="avatar" label="Avatar" width="80">
          <template #default="{ row }">
            <div style="min-height: 32px">
              <img
                v-if="row.avatar"
                style="display: block; width: 32px; height: 32px; border-radius: 50%"
                :src="row.avatar"
                alt=""
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="Email" min-width="200" show-overflow-tooltip />
        <el-table-column prop="phone" label="Phone number" min-width="160" show-overflow-tooltip />
        <el-table-column prop="role" label="Role" width="130">
          <template #default="{ row }">
            {{ row.role === 'admin' ? 'Administrator' : 'Student' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="Status" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'">
              {{ row.status === 1 ? 'Active' : 'Disabled' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleEdit(row)">Edit</el-button>
            <el-button type="danger" link @click="handleDelete(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-pagination">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
          @current-change="load"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="form.id ? 'Edit' : 'Add'" width="450">
      <el-form
        ref="formRef"
        :rules="rules"
        :model="form"
        label-position="top"
        style="width: 100%; padding-top: 8px"
        v-loading="loading"
      >
        <el-form-item label="Username" prop="username">
          <!-- Disable this field when form.id is set, which indicates editing. -->
          <el-input
            :disabled="!!form.id"
            v-model="form.username"
            placeholder="Please enter a username"
          />
        </el-form-item>
        <el-form-item v-if="!form.id" label="Password" prop="password">
          <el-input
            type="password"
            show-password
            v-model="form.password"
            placeholder="Please enter a password"
          />
        </el-form-item>
        <el-form-item label="Name" prop="name">
          <el-input v-model="form.name" placeholder="Please enter a name" />
        </el-form-item>
        <el-form-item label="Role" prop="role">
          <el-select v-model="form.role">
            <el-option label="Student" value="student"></el-option>
            <el-option label="Administrator" value="admin"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="Email" prop="email">
          <el-input v-model="form.email" placeholder="Please enter an email address" />
        </el-form-item>
        <el-form-item label="Phone number" prop="phone">
          <el-input v-model="form.phone" placeholder="Please enter a phone number" />
        </el-form-item>
        <el-form-item label="Status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">Active</el-radio>
            <el-radio :value="0">Disabled</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button>Cancel</el-button>
        <el-button type="primary" :loading="formLoading" @click="handleSave">Confirm</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
defineOptions({ name: 'User' })
import { Search, Plus } from '@element-plus/icons-vue'
import { createUserApi, deleteUserApi, getUserPageList, updateUserApi } from '@/api/user'
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { newPasswordRule, usernameRule } from '@/utils/passwordRules'
const params = reactive({
  page: 1,
  pageSize: 10,
  keywords: ''
})
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  username: '',
  password: '',
  name: '',
  role: 'student',
  email: '',
  phone: '',
  avatar: '',
  status: 1
})
const formLoading = ref(false)

// Editing does not change the password; validate password only when creating a user.
const rules = computed(() => ({
  username: [
    { required: true, message: 'Please enter a username', trigger: 'blur' },
    // An existing username cannot be edited, and older accounts may predate this format.
    ...(form.id ? [] : [usernameRule])
  ],
  ...(form.id
    ? {}
    : {
        password: [
          { required: true, message: 'Please enter a password', trigger: 'blur' },
          newPasswordRule
        ]
      }),
  name: [{ required: true, message: 'Please enter a name', trigger: 'blur' }],
  email: [{ type: 'email', message: 'Invalid email address', trigger: 'blur' }],
  phone: [{ pattern: /^1[3-9]\d{9}$/, message: 'Invalid phone number', trigger: 'blur' }]
}))

const resetForm = () => {
  Object.assign(form, {
    id: null,
    username: '',
    password: '',
    name: '',
    role: 'student',
    email: '',
    phone: '',
    avatar: '',
    status: 1
  })
}

const handleCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (row) => {
  resetForm()
  Object.assign(form, {
    id: row.id,
    username: row.username,
    name: row.name,
    role: row.role,
    email: row.email,
    phone: row.phone,
    avatar: row.avatar,
    status: row.status
  })
  dialogVisible.value = true
}

// Delete user information.
const handleDelete = (row) => {
  ElMessageBox.confirm(`Delete user [${row.username}]?`, 'Confirm deletion', {
    type: 'warning'
  }).then(async () => {
    const res = await deleteUserApi(row.id)
    if (res.code === 200) {
      ElMessage.success('User deleted successfully')
      load()
    }
  })
}

// Save the user.
const handleSave = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  formLoading.value = true
  try {
    let res
    if (form.id) {
      const { password: _pw, ...payload } = form
      res = await updateUserApi(form.id, payload)
    } else {
      res = await createUserApi(form)
    }
    if (res.code === 200) {
      dialogVisible.value = false
      ElMessage.success('Operation successful')
      load()
    }
  } finally {
    formLoading.value = false
  }
}

// Load paginated data.
const load = async () => {
  loading.value = true
  try {
    const res = await getUserPageList({
      page: params.page,
      page_size: params.pageSize,
      keywords: params.keywords
    })
    if (res.code === 200) {
      tableData.value = res.data?.list
      total.value = res.data?.total
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  params.page = 1
  load()
}

onMounted(() => {
  load()
})
</script>
