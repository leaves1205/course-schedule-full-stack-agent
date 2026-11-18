<template>
  <div>
    <el-card>
      <template #header>
        <div style="font-size: 16px; font-weight: bold">My schedule</div>
      </template>
      <div style="margin-bottom: 10px">
        <el-date-picker
          v-model="params.date"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="Filter by date; clear to show all"
          clearable
          @change="handleSearch"
          @clear="handleSearch"
        />
        <el-button style="margin-left: 8px" type="primary" @click="handleSearch">Search</el-button>
      </div>
      <el-table
        :data="tableData"
        v-loading="loading"
        :header-cell-style="{ backgroundColor: '#f5f7fa', color: '#333' }"
      >
        <el-table-column prop="class_date" label="Date" width="140" />
        <el-table-column prop="period" label="Period" width="120" />
        <el-table-column prop="course_name" label="Course" min-width="140" />
        <el-table-column prop="location" label="Location" />
      </el-table>
      <div style="margin-top: 10px; display: flex; justify-content: flex-end">
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
  </div>
</template>
<script setup>
defineOptions({ name: 'Schedule' })
import { onMounted, reactive, ref } from 'vue'
import { listSchedulesApi } from '@/api/schedule'

const params = reactive({
  page: 1,
  pageSize: 10,
  date: null
})
const loading = ref(false)
const tableData = ref([])
const total = ref(0)

const load = async () => {
  loading.value = true
  try {
    const res = await listSchedulesApi({
      page: params.page,
      page_size: params.pageSize,
      date: params.date || undefined
    })
    if (res.code === 200) {
      tableData.value = res.data?.list || []
      total.value = res.data?.total || 0
    }
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  params.page = 1
  load()
}

onMounted(() => {
  load()
})
</script>
