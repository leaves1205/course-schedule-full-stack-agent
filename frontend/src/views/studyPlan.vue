<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">New study plan</div>
      </template>
      <el-form @submit.prevent>
        <el-input
          v-model="content"
          type="textarea"
          :rows="3"
          maxlength="2000"
          show-word-limit
          placeholder="Write and save a study plan for preparation or review"
          aria-label="Study plan content"
        />
        <div style="margin-top: 10px">
          <el-button type="primary" :loading="saving" @click="handleSave">Save</el-button>
        </div>
      </el-form>
      <el-divider />
      <h2 class="section-title">Saved plans</h2>
      <el-table
        :data="tableData"
        v-loading="loading"
        :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#333' }"
      >
        <el-table-column label="Created at" width="180">
          <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column label="Plan content" min-width="280">
          <template #default="{ row }">
            <div class="plan-preview">{{ previewText(row.content) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDetail(row)">View</el-button>
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
    <el-dialog
      v-model="detailVisible"
      title="Plan details"
      width="50%"
      destroy-on-close
      append-to-body
    >
      <div class="detail-meta">Created at: {{ formatTime(detailRow?.create_time) }}</div>
      <div class="plan-md" v-html="parseMarkdown(detailRow?.content)"></div>
    </el-dialog>
  </div>
</template>
<script setup>
defineOptions({ name: 'StudyPlan' })
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { createStudyPlan, deleteStudyPlan, listStudyPlans } from '@/api/studyPlan'

marked.setOptions({
  gfm: true,
  breaks: true
})

const content = ref('')
const saving = ref(false)
const loading = ref(false)
const params = reactive({
  page: 1,
  pageSize: 10
})
const tableData = ref([])
const total = ref(0)
const detailVisible = ref(false)
const detailRow = ref(null)

const parseMarkdown = (text) => {
  if (!text) return ''
  const rawHtml = marked.parse(String(text).replace(/\r\n/g, '\n'))
  return DOMPurify.sanitize(rawHtml, { USE_PROFILES: { html: true } })
}

const previewText = (text, maxLen = 120) => {
  if (!text) return '-'
  const plain = String(text)
    .replace(/\r\n/g, '\n')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/\|/g, ' ')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_~`>#\-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  if (!plain) return '-'
  return plain.length > maxLen ? `${plain.slice(0, maxLen)}…` : plain
}

const formatTime = (value) => {
  if (!value) return '-'
  const text = String(value).replace('T', ' ')
  return text.length >= 19 ? text.slice(0, 19) : text
}

const openDetail = (row) => {
  detailRow.value = row
  detailVisible.value = true
}

const load = async () => {
  loading.value = true
  try {
    const res = await listStudyPlans({
      page: params.page,
      page_size: params.pageSize
    })
    if (res.code === 200) {
      tableData.value = res.data?.list || []
      total.value = res.data?.total || 0
    }
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  if (!content.value.trim()) {
    ElMessage.warning('Please enter plan content')
    return
  }
  saving.value = true
  try {
    const res = await createStudyPlan(content.value.trim())
    if (res.code === 200) {
      ElMessage.success('Saved')
      content.value = ''
      params.page = 1
      await load()
    }
  } finally {
    saving.value = false
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm('Delete this study plan?', 'Confirm deletion', { type: 'warning' }).then(
    async () => {
      const res = await deleteStudyPlan(row.id)
      if (res.code === 200) {
        ElMessage.success('Deleted')
        await load()
      }
    }
  )
}

onMounted(() => {
  load()
})
</script>
<style scoped>
.plan-preview {
  line-height: 1.5;
  color: #606266;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.detail-meta {
  margin-bottom: 12px;
  color: #909399;
  font-size: 13px;
}
.plan-md {
  line-height: 1.6;
  overflow-x: auto;
  max-height: 60vh;
  overflow-y: auto;
  padding: 4px 0;
}
.plan-md :deep(p) {
  margin: 0.35em 0;
}
.plan-md :deep(ul),
.plan-md :deep(ol) {
  margin: 0.35em 0;
  padding-left: 1.3em;
}
</style>
