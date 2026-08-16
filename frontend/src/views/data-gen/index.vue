<template>
  <div class="datagen-page">
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('dataGen.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="$router.push('/projects')">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item><span class="current-crumb">{{ t('dataGen.breadcrumb.title') }}</span></el-breadcrumb-item>
        </el-breadcrumb>
        <div class="subtitle">{{ t('dataGen.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-input-number v-model="rowsPerTable" :min="1" :max="500" size="small" />
        <el-button type="primary" :icon="MagicStick" :loading="generating" @click="handleGenerate(false)">
          {{ t('dataGen.generateSql') }}
        </el-button>
        <el-button type="danger" plain :icon="Promotion" :loading="generating" @click="handleGenerate(true)">
          {{ t('dataGen.directInsert') }}
        </el-button>
        <el-button :icon="Back" @click="$router.push(`/projects/${projectId}/er-model`)">
          {{ t('dataGen.backToEr') }}
        </el-button>
      </div>
    </div>

    <div class="datagen-body">
      <div v-if="!result" class="empty-state">
        <el-empty :description="t('dataGen.empty')" :image-size="140" />
      </div>
      <template v-else>
        <div class="summary-bar">
          <el-tag type="success" effect="light" round>{{ t('dataGen.tables', { count: Object.keys(result.row_counts).length }) }}</el-tag>
          <el-tag type="primary" effect="light" round>{{ t('dataGen.rows', { count: result.total_rows }) }}</el-tag>
          <el-tag v-if="result.executed > 0" type="warning" effect="light" round>{{ t('dataGen.executed', { count: result.executed }) }}</el-tag>
          <el-tag v-if="result.error" type="danger" effect="light" round>{{ t('dataGen.error') }}</el-tag>
          <el-button size="small" :icon="Download" @click="downloadSql">{{ t('dataGen.downloadSql') }}</el-button>
        </div>
        <pre v-if="result.error" class="error-block">{{ result.error }}</pre>
        <pre class="sql-block">{{ sqlText }}</pre>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { generateTestData } from '@/api/dataGen'
import { getProject } from '@/api/project'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const rowsPerTable = ref(10)
const generating = ref(false)
const result = ref(null)

const sqlText = computed(() => (result.value?.sql || []).join('\n'))

const handleGenerate = async (execute) => {
  if (execute) {
    try {
      await ElMessageBox.confirm(t('dataGen.insertConfirm'), t('dataGen.directInsert'), {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      })
    } catch {
      return
    }
  }
  generating.value = true
  try {
    result.value = await generateTestData(projectId.value, {
      rows_per_table: rowsPerTable.value,
      execute
    })
    if (execute && result.value.executed > 0) {
      ElMessage.success(t('dataGen.inserted', { count: result.value.executed }))
    }
  } catch {
    // interceptor shows error
  } finally {
    generating.value = false
  }
}

const downloadSql = () => {
  const blob = new Blob([sqlText.value], { type: 'application/sql;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'test-data.sql'
  a.click()
  URL.revokeObjectURL(url)
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

.datagen-page { width: 100%; height: 100%; display: flex; flex-direction: column; background: $bg-color; }
.page-header {
  min-height: 64px; background: $bg-white; border-bottom: 1px solid $border-light;
  padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.subtitle { font-size: 12px; color: #94A3B8; }
.current-crumb { color: #1E293B; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.datagen-body { flex: 1; overflow: auto; padding: 20px; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; }
.summary-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.sql-block {
  max-height: calc(100vh - 260px); overflow: auto; background: #0f172a; color: #e2e8f0;
  border-radius: 10px; padding: 16px; font-family: 'SF Mono', Consolas, monospace; font-size: 12px; line-height: 1.6; white-space: pre-wrap;
}
.error-block {
  background: rgba(239, 68, 68, 0.08); color: #dc2626; border-radius: 8px; padding: 12px; margin-bottom: 10px;
  font-family: 'SF Mono', Consolas, monospace; font-size: 12px; white-space: pre-wrap;
}
html.dark {
  .page-header { background: #252526 !important; border-bottom-color: #3c3c3c !important; }
  .current-crumb { color: #f8fafc !important; }
  .datagen-page { background: #1e1e1e !important; }
}
</style>
