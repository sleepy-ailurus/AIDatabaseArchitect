<template>
  <div class="doc-page">
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('designDoc.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="$router.push('/projects')">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item><span class="current-crumb">{{ t('designDoc.breadcrumb.title') }}</span></el-breadcrumb-item>
        </el-breadcrumb>
        <div class="subtitle">{{ t('designDoc.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-button :icon="Download" type="success" :loading="exporting" @click="doExport('markdown')">Markdown</el-button>
        <el-button :icon="Download" :loading="exporting" @click="doExport('word')">Word</el-button>
        <el-button :icon="Back" @click="$router.push(`/projects/${projectId}/er-model`)">
          {{ t('designDoc.backToEr') }}
        </el-button>
      </div>
    </div>

    <div class="doc-body" v-loading="previewing">
      <div class="doc-preview">
        <el-scrollbar class="doc-scroll">
          <div class="md-content" v-if="previewText">
            <pre class="raw-md">{{ previewText }}</pre>
          </div>
          <el-empty v-else :description="t('designDoc.empty')" :image-size="120" />
        </el-scrollbar>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { exportDesignDoc } from '@/api/docs'
import { getProject } from '@/api/project'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const previewText = ref('')
const exporting = ref(false)
const previewing = ref(false)

const doExport = async (format) => {
  exporting.value = true
  try {
    const blob = await exportDesignDoc(projectId.value, format, {
      author: '',
      student_id: ''
    })
    if (format === 'markdown') {
      previewing.value = true
      try {
        previewText.value = await blob.text()
      } finally {
        previewing.value = false
      }
    } else {
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `design-doc.${format}`
      a.click()
      URL.revokeObjectURL(url)
      ElMessage.success(t('designDoc.exported', { format: format.toUpperCase() }))
    }
  } catch {
    // interceptor shows error
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  try {
    const data = await getProject(projectId.value)
    if (data) projectName.value = data.name
  } catch {
    // ignore
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.doc-page { width: 100%; height: 100%; display: flex; flex-direction: column; background: $bg-color; }
.page-header {
  min-height: 64px; background: $bg-white; border-bottom: 1px solid $border-light;
  padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.subtitle { font-size: 12px; color: #94A3B8; }
.current-crumb { color: #1E293B; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.doc-body { flex: 1; overflow: hidden; padding: 20px; }
.doc-preview {
  height: 100%; background: $bg-white; border: 1px solid $border-light; border-radius: 12px; overflow: hidden;
}
.doc-scroll { height: 100%; }
.raw-md {
  padding: 24px 28px; font-family: 'SF Mono', Consolas, monospace; font-size: 12px; line-height: 1.7;
  color: $text-regular; white-space: pre-wrap; word-break: break-word;
}
html.dark {
  .page-header { background: #252526 !important; border-bottom-color: #3c3c3c !important; }
  .current-crumb { color: #f8fafc !important; }
  .doc-preview { background: #252526 !important; border-color: #3c3c3c !important; }
  .raw-md { color: #cbd5e1 !important; }
}
</style>
