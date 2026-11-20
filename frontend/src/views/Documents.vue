<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">Course documents</div>
      </template>

      <div v-if="isAdmin" style="margin-bottom: 12px">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :disabled="uploadLoading"
          :show-file-list="true"
          multiple
          accept=".txt,.md,.pdf,.docx,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          :on-change="onFileChange"
          :on-remove="onFileRemove"
        >
          <el-button type="primary" :disabled="uploadLoading">Select files</el-button>
        </el-upload>
        <el-button
          style="margin-top: 8px"
          type="primary"
          :loading="uploadLoading"
          :disabled="!pendingFiles.length"
          @click="handleUpload"
        >
          Upload documents
        </el-button>
        <div style="margin-top: 6px; color: #909399; font-size: 12px">
          Supports .txt / .md / .pdf / .docx, up to 100 MiB per file. Duplicate filenames are not allowed; scanned PDFs
          may not contain extractable text. If any upload in a batch fails, the entire batch is rolled back.
        </div>
      </div>
      <div v-else style="margin-bottom: 12px; color: #909399; font-size: 13px">
        Only administrators can manage knowledge base documents.
      </div>

      <el-table
        v-loading="loading"
        :data="pageData"
        :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#333' }"
      >
        <el-table-column
          prop="original_name"
          label="Filename"
          min-width="180"
          show-overflow-tooltip
        />
        <el-table-column prop="size" label="Size" width="100">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="ext" label="Type" width="80" />
        <el-table-column label="Created at" width="180">
          <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column v-if="isAdmin" label="Actions" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handlePreview(row)">
              Preview
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)"> Delete </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          background
          layout="total, prev, pager, next"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="720px"
      destroy-on-close
      append-to-body
    >
      <div class="preview-meta" v-if="previewMeta">{{ previewMeta }}</div>
      <div v-loading="previewLoading" class="preview-body">
        <pre v-if="previewText" class="preview-text">{{ previewText }}</pre>
        <div v-else-if="!previewLoading" style="color: #909399">No text available</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteDocumentApi,
  listDocumentsApi,
  previewDocumentApi,
  uploadDocumentsApi
} from '@/api/document'
import { useUser } from '@/utils/user'

const { userInfo } = useUser()
const isAdmin = computed(() => userInfo.value?.role === 'admin')
const loading = ref(false)
const allData = ref([])
const page = ref(1)
const pageSize = ref(10)
const pendingFiles = ref([])
const uploadLoading = ref(false)
const uploadRef = ref()
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewTitle = ref('Document preview')
const previewMeta = ref('')
const previewText = ref('')
let previewRequestId = 0 // Track the latest preview so older requests cannot overwrite the current document
const total = computed(() => allData.value.length)
const pageData = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return allData.value.slice(start, start + pageSize.value)
})

const load = async () => {
  loading.value = true
  try {
    const res = await listDocumentsApi()
    // Business errors may still resolve the promise; update the list only when code=200.
    if (res.code === 200) {
      allData.value = res.data
      const maxPage = Math.max(1, Math.ceil(res.data.length / pageSize.value))
      page.value = Math.min(page.value, maxPage)
    }
  } catch {
    // Network and HTTP errors have already been displayed by the request interceptor.
  } finally {
    loading.value = false
  }
}

const onFileChange = (_file, fileList) => {
  pendingFiles.value = fileList.map((file) => file.raw)
}
const onFileRemove = (_file, fileList) => {
  pendingFiles.value = fileList.map((file) => file.raw)
}

const handleUpload = async () => {
  // Skip requests when no files are selected or an upload is already in progress.
  if (!pendingFiles.value.length || uploadLoading.value) return
  uploadLoading.value = true
  try {
    const res = await uploadDocumentsApi(pendingFiles.value)
    // Clear the selection only after the entire batch succeeds; keep it on failure so invalid files can be removed before retrying.
    if (res.code === 200) {
      ElMessage.success('Upload successful')
      pendingFiles.value = []
      uploadRef.value.clearFiles()
      page.value = 1
      await load()
    }
  } catch {
    // The error has already been displayed; keep the pending files.
  } finally {
    uploadLoading.value = false
  }
}

const handlePreview = async (row) => {
  const requestId = ++previewRequestId
  previewTitle.value = `Preview: ${row.original_name}`
  previewMeta.value = ''
  previewText.value = ''
  previewVisible.value = true
  previewLoading.value = true
  try {
    const res = await previewDocumentApi(row.id)
    // Ignore a delayed response if the user has already opened another document.
    if (requestId !== previewRequestId) return
    // Show the current file's error on parsing failure without retaining text from the previous document.
    if (res.code === 200) {
      previewText.value = res.data.text
      previewMeta.value = `Plain text extracted: ${res.data.char_count} characters`
    } else {
      previewMeta.value = 'Preview unavailable. Check the file using the error details.'
    }
  } catch {
    if (requestId === previewRequestId) {
      previewMeta.value = 'Preview request failed. Please try again later.'
    }
  } finally {
    if (requestId === previewRequestId) previewLoading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`Delete the document "${row.original_name}" and its original file?`, 'Confirm deletion', {
      type: 'warning'
    })
  } catch {
    // Do not call the delete API if the confirmation dialog is canceled or closed.
    return
  }
  try {
    const res = await deleteDocumentApi(row.id)
    if (res.code === 200) {
      ElMessage.success('Deleted')
      await load()
    }
  } catch {
    // The error has already been displayed by the request interceptor.
  }
}

const formatSize = (n) => {
  // Choose the display unit based on file size, using 1024 as the conversion base.
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}
const formatTime = (value) => String(value).replace('T', ' ').slice(0, 19)

onMounted(() => {
  // Skip loading documents when students navigate directly to this URL; the backend still checks permissions on every endpoint.
  if (isAdmin.value) load()
})
</script>

<style scoped>
.preview-meta {
  margin-bottom: 10px;
  color: #909399;
  font-size: 13px;
}
.preview-body {
  min-height: 120px;
}
.preview-text {
  margin: 0;
  max-height: 60vh;
  overflow: auto;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
  font-family: ui-monospace, Consolas, 'Courier New', monospace;
}
</style>
