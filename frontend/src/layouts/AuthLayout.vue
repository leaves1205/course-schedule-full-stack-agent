<template>
  <div class="auth-layout">
    <header class="auth-header">
      <RouterLink to="/login" class="auth-brand"
        ><span
          ><el-icon><Reading /></el-icon></span
        >CourseFlow</RouterLink
      >
    </header>
    <main class="auth-main">
      <section class="auth-panel">
        <h1>{{ title }}</h1>
        <p class="auth-description">{{ description }}</p>
        <slot />
        <div class="auth-switch"><slot name="switch" /></div>
      </section>
      <p class="auth-footer">Course schedule management</p>
    </main>
  </div>
</template>

<script setup>
import { Reading } from '@element-plus/icons-vue'
defineProps({ title: String, description: String })
</script>

<style scoped>
.auth-layout {
  min-height: 100dvh;
  background: #fff;
}
.auth-header {
  height: 64px;
  padding: 0 32px;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--workspace-border);
}
.auth-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #182230;
  font-size: 18px;
  font-weight: 600;
}
.auth-brand > span {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 5px;
  background: #1668dc;
  color: white;
  font-size: 20px;
}
.auth-main {
  padding: clamp(40px, 10vh, 100px) 20px 32px;
}
.auth-panel {
  width: 100%;
  max-width: 420px;
  margin: 0 auto;
  padding: 32px;
  border: 1px solid var(--workspace-border);
  border-radius: 6px;
}
h1 {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.4;
}
.auth-description {
  margin-top: 8px;
  margin-bottom: 28px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--workspace-muted);
}
.auth-switch {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--workspace-border);
  font-size: 13px;
  text-align: center;
  color: #697586;
}
.auth-switch :deep(a) {
  color: var(--el-color-primary);
  margin-left: 4px;
}
.auth-switch :deep(a:hover) {
  text-decoration: underline;
}
.auth-footer {
  text-align: center;
  color: var(--workspace-muted);
  font-size: 12px;
  margin-top: 24px;
}
@media (max-width: 600px) {
  .auth-header {
    padding-inline: 20px;
  }
  .auth-panel {
    padding: 24px;
  }
  .auth-main {
    padding-top: 40px;
  }
}
</style>
