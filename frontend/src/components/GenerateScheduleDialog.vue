<template>
  <el-dialog
    :model-value="modelValue"
    title="Generate semester schedule"
    width="820px"
    destroy-on-close
    :close-on-click-modal="!saving"
    :before-close="close"
  >
    <el-alert v-if="!semesters.length" type="info" :closable="false" show-icon
      ><template #title
        >Create a semester first in
        <RouterLink to="/manager/semesters" @click="close()" class="semester-link"
          >Semesters</RouterLink
        >.</template
      ></el-alert
    >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      :disabled="saving"
      label-position="top"
      class="generation-form"
    >
      <div class="form-grid">
        <el-form-item label="Semester" prop="semester_id"
          ><el-select
            v-model="form.semester_id"
            placeholder="Select semester"
            @change="selectSemester"
            ><el-option
              v-for="item in semesters"
              :key="item.id"
              :label="`${item.name} · ${item.total_weeks} weeks`"
              :value="item.id" /></el-select
        ></el-form-item>
        <el-form-item label="Student" prop="user_id"
          ><el-select v-model="form.user_id" placeholder="Select student" filterable
            ><el-option
              v-for="item in students"
              :key="item.id"
              :label="`${item.name} (${item.username})`"
              :value="item.id" /></el-select
        ></el-form-item>
        <el-form-item label="Course" prop="course_id"
          ><el-select v-model="form.course_id" placeholder="Select course" filterable
            ><el-option
              v-for="item in courses"
              :key="item.id"
              :label="item.code ? `${item.name} (${item.code})` : item.name"
              :value="item.id" /></el-select
        ></el-form-item>
        <div class="week-range">
          <el-form-item label="First week" prop="start_week"
            ><el-input-number
              v-model="form.start_week"
              :min="1"
              :max="maxWeeks"
              controls-position="right" /></el-form-item
          ><el-form-item label="Last week" prop="end_week"
            ><el-input-number
              v-model="form.end_week"
              :min="form.start_week || 1"
              :max="maxWeeks"
              controls-position="right"
          /></el-form-item>
        </div>
      </div>
      <div class="meeting-heading">
        <h3>Weekly classes</h3>
        <el-button :icon="Plus" :disabled="form.meetings.length >= 35 || saving" @click="addMeeting"
          >Add weekly class</el-button
        >
      </div>
      <div v-for="(meeting, index) in form.meetings" :key="meeting.key" class="meeting-row">
        <el-form-item
          label="Day"
          :prop="`meetings.${index}.weekday`"
          :rules="{ required: true, message: 'Select a day', trigger: 'change' }"
          ><el-select v-model="meeting.weekday" :aria-label="`Day for weekly class ${index + 1}`"
            ><el-option
              v-for="(day, dayIndex) in weekdays"
              :key="day"
              :label="day"
              :value="dayIndex + 1" /></el-select
        ></el-form-item>
        <el-form-item
          label="First period"
          :prop="`meetings.${index}.start_period`"
          :rules="{ required: true, message: 'Enter a period', trigger: 'change' }"
          ><el-input-number
            v-model="meeting.start_period"
            :min="1"
            :max="30"
            controls-position="right"
            :aria-label="`First period for weekly class ${index + 1}`"
        /></el-form-item>
        <el-form-item
          label="Last period"
          :prop="`meetings.${index}.end_period`"
          :rules="{ required: true, message: 'Enter a period', trigger: 'change' }"
          ><el-input-number
            v-model="meeting.end_period"
            :min="meeting.start_period || 1"
            :max="30"
            controls-position="right"
            :aria-label="`Last period for weekly class ${index + 1}`"
        /></el-form-item>
        <el-form-item label="Location"
          ><el-input
            v-model="meeting.location"
            maxlength="100"
            placeholder="For example: A201"
            :aria-label="`Location for weekly class ${index + 1}`"
        /></el-form-item>
        <el-button
          class="remove-meeting"
          :icon="Delete"
          :aria-label="`Remove weekly class ${index + 1}`"
          :disabled="form.meetings.length === 1 || saving"
          @click="form.meetings.splice(index, 1)"
        />
      </div>
    </el-form>
    <div class="generation-summary" aria-live="polite">
      <strong>{{ sessionCount }} planned classes</strong
      ><span
        >Weeks {{ form.start_week || '—' }}–{{ form.end_week || '—' }} · {{ form.meetings.length }}
        {{ form.meetings.length === 1 ? 'class' : 'classes' }} per week</span
      >
      <p v-if="dateRange">{{ dateRange }}</p>
      <p>
        Existing classes and single-class changes are preserved when the same rules are generated
        again.
      </p>
    </div>
    <div v-if="conflicts.length" class="conflict-report" role="alert">
      <el-alert
        :title="`${conflictCount} conflicts found. Nothing was saved.`"
        type="error"
        :closable="false"
        show-icon
      /><el-table :data="conflicts" max-height="220"
        ><el-table-column prop="date" label="Date" width="120" /><el-table-column
          prop="requested_period"
          label="Requested"
          width="110" /><el-table-column
          prop="existing_period"
          label="Conflicts with"
          width="120" /><el-table-column prop="message" label="Details" min-width="220"
      /></el-table>
      <p v-if="conflictCount > conflicts.length">
        Showing the first {{ conflicts.length }} conflicts.
      </p>
    </div>
    <template #footer
      ><el-button :disabled="saving" @click="close()">Cancel</el-button
      ><el-button
        type="primary"
        :loading="saving"
        :disabled="!semesters.length || !sessionCount"
        @click="generate"
        >Generate {{ sessionCount }} classes</el-button
      ></template
    >
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { generateSchedulesApi } from '@/api/schedule'

const props = defineProps({
  modelValue: Boolean,
  semesters: { type: Array, default: () => [] },
  students: { type: Array, default: () => [] },
  courses: { type: Array, default: () => [] },
  semesterId: Number,
  userId: Number
})
const emit = defineEmits(['update:modelValue', 'generated'])
const formRef = ref()
const saving = ref(false)
const conflicts = ref([])
const conflictCount = ref(0)
const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
let nextKey = 0
const newMeeting = () => ({
  key: nextKey++,
  weekday: 1,
  start_period: 1,
  end_period: 2,
  location: ''
})
const form = reactive({
  semester_id: null,
  user_id: null,
  course_id: null,
  start_week: 1,
  end_week: 16,
  meetings: [newMeeting()]
})
const selectedSemester = computed(() =>
  props.semesters.find((item) => item.id === form.semester_id)
)
const maxWeeks = computed(() => selectedSemester.value?.total_weeks || 60)
const sessionCount = computed(
  () => Math.max(0, (form.end_week || 0) - (form.start_week || 0) + 1) * form.meetings.length
)
const dateRange = computed(() => {
  if (!selectedSemester.value || !form.start_week || !form.end_week) return ''
  const dates = form.meetings.flatMap((item) =>
    [form.start_week, form.end_week].map((week) => {
      const day = new Date(`${selectedSemester.value.first_monday}T00:00:00`)
      day.setDate(day.getDate() + (week - 1) * 7 + item.weekday - 1)
      return day
    })
  )
  const format = (day) =>
    day.toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' })
  return `${format(new Date(Math.min(...dates)))} – ${format(new Date(Math.max(...dates)))}`
})
const rules = {
  semester_id: [{ required: true, message: 'Select a semester', trigger: 'change' }],
  user_id: [{ required: true, message: 'Select a student', trigger: 'change' }],
  course_id: [{ required: true, message: 'Select a course', trigger: 'change' }],
  start_week: [{ required: true, message: 'Enter the first week', trigger: 'change' }],
  end_week: [{ required: true, message: 'Enter the last week', trigger: 'change' }]
}
watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    Object.assign(form, {
      semester_id: props.semesterId || props.semesters[0]?.id || null,
      user_id: props.userId || null,
      course_id: null,
      start_week: 1,
      end_week: 16,
      meetings: [newMeeting()]
    })
    form.end_week = selectedSemester.value?.total_weeks || 16
    conflicts.value = []
  },
  { immediate: true }
)
function selectSemester() {
  form.start_week = 1
  form.end_week = maxWeeks.value
  conflicts.value = []
}
function addMeeting() {
  const item = newMeeting()
  item.weekday = 4
  form.meetings.push(item)
}
function close(done) {
  if (saving.value) return
  emit('update:modelValue', false)
  if (typeof done === 'function') done()
}
async function generate() {
  if (saving.value) return
  saving.value = true
  conflicts.value = []
  try {
    if (!(await formRef.value.validate().catch(() => false))) return
    if (
      form.start_week > form.end_week ||
      form.end_week > maxWeeks.value ||
      form.meetings.some((item) => item.end_period < item.start_period)
    ) {
      ElMessage.warning('Check the week and period ranges')
      return
    }
    const result = await generateSchedulesApi({
      semester_id: form.semester_id,
      user_id: form.user_id,
      course_id: form.course_id,
      start_week: form.start_week,
      end_week: form.end_week,
      meetings: form.meetings.map(({ key, ...meeting }) => ({ ...meeting }))
    })
    if (result.code === 200) {
      ElMessage.success(
        `Created ${result.data.created_count} classes; preserved ${result.data.preserved_count} existing classes`
      )
      emit('generated', { semesterId: form.semester_id, userId: form.user_id })
      emit('update:modelValue', false)
    } else {
      conflicts.value = result.data?.conflicts || []
      conflictCount.value = result.data?.conflict_count || conflicts.value.length
    }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.generation-form {
  margin-top: 16px;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 20px;
}
.week-range {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.week-range .el-input-number {
  width: 100%;
}
.meeting-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding-top: 8px;
  margin-bottom: 16px;
  border-top: 1px solid var(--workspace-border);
}
.meeting-heading h3 {
  font-size: 15px;
  font-weight: 600;
}
.meeting-row {
  display: grid;
  grid-template-columns: 1.3fr 1fr 1fr 1.4fr 32px;
  gap: 12px;
  align-items: start;
}
.meeting-row .el-input-number {
  width: 100%;
}
.remove-meeting {
  margin: 30px 0 0;
}
.generation-summary {
  background: #f5f8fd;
  border: 1px solid #dce7f7;
  border-radius: 4px;
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.7;
}
.generation-summary strong {
  display: block;
  color: var(--el-color-primary);
  font-size: 15px;
}
.generation-summary p {
  color: var(--workspace-muted);
  margin-top: 4px;
  font-size: 12px;
}
.conflict-report {
  margin-top: 16px;
}
.conflict-report > p {
  font-size: 12px;
  margin-top: 8px;
}
.semester-link {
  color: var(--el-color-primary);
  text-decoration: underline;
}
@media (max-width: 600px) {
  .form-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .meeting-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 12px;
    margin-bottom: 12px;
    border: 1px solid var(--workspace-border);
    border-radius: 4px;
  }
  .remove-meeting {
    margin: 0;
  }
  .meeting-heading {
    flex-wrap: wrap;
  }
}
</style>
