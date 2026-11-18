<template>
  <div>
    <el-card shadow="never">
      <div style="font-size: 18px; color: #333">Welcome, {{ userInfo?.name || 'Student' }}</div>
    </el-card>
  </div>
</template>

<script setup>
import { useUser } from '@/utils/user'
const { userInfo } = useUser()
</script>
