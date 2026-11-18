<template>
  <div>
    <el-card>
      <template #header
        ><div class="semester-header">
          <span>Teaching semesters</span
          ><el-button type="primary" :icon="Plus" @click="openForm()">Add semester</el-button>
        </div></template
      >
      <el-table :data="semesters" v-loading="loading">
        <el-table-column prop="name" label="Semester" min-width="180" />
        <el-table-column prop="first_monday" label="First teaching Monday" width="190" />
        <el-table-column prop="total_weeks" label="Weeks" width="90" />
        <el-table-column prop="end_date" label="Last teaching Sunday" width="190" />
        <el-table-column prop="rule_count" label="Weekly rules" width="120" />
        <el-table-column label="Actions" width="180" fixed="right"
          ><template #default="{ row }"
            ><el-button type="primary" link @click="openForm(row)">Edit</el-button
            ><el-button type="danger" link :disabled="row.rule_count > 0" @click="remove(row)"
              >Delete</el-button
            ></template
          ></el-table-column
        >
        <template #empty>No semesters yet. Add one before generating weekly classes.</template>
      </el-table>
    </el-card>
    <el-dialog
      v-model="visible"
      :title="form.id ? 'Edit semester' : 'Add semester'"
      width="480px"
      destroy-on-close
      :close-on-click-modal="!saving"
    >
      <el-alert
        v-if="form.rule_count"
        title="This semester has weekly rules. Its teaching dates are locked; you can still rename it."
        type="info"
        :closable="false"
        show-icon
        class="semester-notice"
      />
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="save"
      >
        <el-form-item label="Semester name" prop="name"
          ><el-input
            v-model="form.name"
            placeholder="For example: Semester 1, 2027"
            maxlength="100"
        /></el-form-item>
        <el-form-item label="Monday of the first teaching week" prop="first_monday"
          ><el-date-picker
            v-model="form.first_monday"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="Select a Monday"
            :disabled="!!form.rule_count"
            :disabled-date="disabledDate"
            style="width: 100%"
        /></el-form-item>
        <el-form-item label="Number of teaching weeks" prop="total_weeks"
          ><el-input-number
            v-model="form.total_weeks"
            :min="1"
            :max="60"
            :disabled="!!form.rule_count"
            controls-position="right"
        /></el-form-item>
      </el-form>
      <template #footer
        ><el-button :disabled="saving" @click="visible = false">Cancel</el-button
        ><el-button type="primary" :loading="saving" @click="save"
          >Save semester</el-button
        ></template
      >
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listSemestersApi,
  createSemesterApi,
  updateSemesterApi,
  deleteSemesterApi
} from '@/api/semester'

const semesters = ref([])
const loading = ref(false)
const visible = ref(false)
const saving = ref(false)
const formRef = ref()
const form = reactive({ id: null, name: '', first_monday: '', total_weeks: 16, rule_count: 0 })
const rules = {
  name: [{ required: true, message: 'Enter a semester name', trigger: 'blur' }],
  first_monday: [
    { required: true, message: 'Select the first teaching Monday', trigger: 'change' }
  ],
  total_weeks: [{ required: true, message: 'Enter the number of weeks', trigger: 'change' }]
}
const disabledDate = (value) => value.getDay() !== 1
async function load() {
  loading.value = true
  try {
    const result = await listSemestersApi()
    if (result.code === 200) semesters.value = result.data || []
  } finally {
    loading.value = false
  }
}
function openForm(row) {
  Object.assign(
    form,
    row || { id: null, name: '', first_monday: '', total_weeks: 16, rule_count: 0 }
  )
  visible.value = true
}
async function save() {
  if (saving.value || !(await formRef.value.validate().catch(() => false))) return
  saving.value = true
  try {
    const data = { name: form.name, first_monday: form.first_monday, total_weeks: form.total_weeks }
    const result = form.id ? await updateSemesterApi(form.id, data) : await createSemesterApi(data)
    if (result.code === 200) {
      visible.value = false
      ElMessage.success('Semester saved')
      await load()
    }
  } finally {
    saving.value = false
  }
}
async function remove(row) {
  if (
    !(await ElMessageBox.confirm(`Delete semester "${row.name}"?`, 'Delete semester', {
      type: 'warning'
    })
      .then(() => true)
      .catch(() => false))
  )
    return
  const result = await deleteSemesterApi(row.id)
  if (result.code === 200) {
    ElMessage.success('Semester deleted')
    await load()
  }
}
onMounted(load)
</script>

<style scoped>
.semester-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.semester-notice {
  margin-bottom: 20px;
}
</style>
