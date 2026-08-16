<template>
  <div class="domains-page">
    <div class="page-header">
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb-sm">
          <el-breadcrumb-item style="color: #94A3B8;">{{ t('domains.breadcrumb.project') }}</el-breadcrumb-item>
          <el-breadcrumb-item style="color: #94A3B8; cursor: pointer;" @click="$router.push('/projects')">{{ projectName }}</el-breadcrumb-item>
          <el-breadcrumb-item><span class="current-crumb">{{ t('domains.breadcrumb.title') }}</span></el-breadcrumb-item>
        </el-breadcrumb>
        <div class="subtitle">{{ t('domains.subtitle') }}</div>
      </div>
      <div class="header-actions">
        <el-checkbox v-model="useAiNames">{{ t('domains.aiNames') }}</el-checkbox>
        <el-button type="primary" :icon="MagicStick" :loading="analyzing" @click="handleAnalyze">
          {{ t('domains.analyze') }}
        </el-button>
        <el-button :icon="Back" @click="$router.push(`/projects/${projectId}/er-model`)">
          {{ t('domains.backToEr') }}
        </el-button>
      </div>
    </div>

    <div class="domains-body" v-loading="loading">
      <div v-if="clusters.length === 0" class="empty-state">
        <el-empty :description="t('domains.empty')" :image-size="140" />
      </div>
      <div v-else class="cluster-grid">
        <div
          v-for="c in clusters"
          :key="c.cluster_index"
          class="cluster-card"
          @click="goToEr(c.cluster_index)"
        >
          <div class="cluster-head">
            <div class="cluster-index">{{ c.cluster_index + 1 }}</div>
            <div class="cluster-info">
            <div class="cluster-name">{{ displayName(c) }}</div>
              <div class="cluster-desc" v-if="c.description">{{ c.description }}</div>
            </div>
            <el-tag size="small" type="warning" effect="light" round>{{ c.tables.length }} {{ t('domains.tables') }}</el-tag>
          </div>
          <div class="cluster-tables">
            <el-tag v-for="t in c.tables" :key="t" size="small" effect="plain" type="info" round class="table-tag">
              {{ t }}
            </el-tag>
          </div>
          <div class="cluster-action">{{ t('domains.viewInCanvas') }} <el-icon><Right /></el-icon></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { analyzeDomains, getDomains } from '@/api/domains'
import { getProject } from '@/api/project'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const projectId = computed(() => route.params.id)

const projectName = ref('')
const clusters = ref([])
const loading = ref(false)
const analyzing = ref(false)
const useAiNames = ref(false)

const displayName = (c) => {
  const m = /^业务域\s*(\d+)$/.exec(c.name || '')
  if (m) return t('domains.domainN', { n: m[1] })
  return c.name || ''
}

const load = async () => {
  loading.value = true
  try {
    clusters.value = await getDomains(projectId.value)
  } catch {
    clusters.value = []
  } finally {
    loading.value = false
  }
}

const handleAnalyze = async () => {
  if (useAiNames.value) {
    try {
      await ElMessageBox.confirm(t('domains.aiConfirm'), t('domains.analyze'), {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'info'
      })
    } catch {
      return
    }
  }
  analyzing.value = true
  try {
    clusters.value = await analyzeDomains(projectId.value, {
      use_ai_names: useAiNames.value,
      lang: locale.value
    })
    ElMessage.success(t('domains.analyzed', { count: clusters.value.length }))
  } catch {
    // interceptor shows error
  } finally {
    analyzing.value = false
  }
}

const goToEr = (index) => {
  router.push(`/projects/${projectId.value}/er-model?domain=${index}`)
}

onMounted(async () => {
  try {
    const data = await getProject(projectId.value)
    if (data) projectName.value = data.name
  } catch {
    // ignore
  }
  await load()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.domains-page { width: 100%; height: 100%; display: flex; flex-direction: column; background: $bg-color; }
.page-header {
  min-height: 64px; background: $bg-white; border-bottom: 1px solid $border-light;
  padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.subtitle { font-size: 12px; color: #94A3B8; }
.current-crumb { color: #1E293B; font-weight: 600; }
.header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.domains-body { flex: 1; overflow: auto; padding: 20px; }
.empty-state { display: flex; align-items: center; justify-content: center; height: 100%; }
.cluster-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
.cluster-card {
  background: $bg-white; border: 1px solid $border-light; border-radius: 12px; padding: 16px;
  cursor: pointer; transition: all 0.18s;
  &:hover { border-color: #f59e0b; box-shadow: 0 4px 16px rgba(245, 158, 11, 0.15); transform: translateY(-2px); }
}
.cluster-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.cluster-index {
  width: 30px; height: 30px; border-radius: 8px; background: rgba(245, 158, 11, 0.12);
  color: #b45309; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.cluster-info { flex: 1; min-width: 0; }
.cluster-name { font-size: 15px; font-weight: 700; color: $text-primary; }
.cluster-desc { font-size: 12px; color: #64748b; margin-top: 2px; }
.cluster-tables { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.table-tag { font-family: 'SF Mono', Consolas, monospace; }
.cluster-action { font-size: 12px; color: #f59e0b; display: flex; align-items: center; gap: 4px; }

html.dark {
  .page-header { background: #252526 !important; border-bottom-color: #3c3c3c !important; }
  .current-crumb { color: #f8fafc !important; }
  .cluster-card { background: #252526 !important; border-color: #3c3c3c !important; }
  .cluster-name { color: #f8fafc !important; }
  .domains-page { background: #1e1e1e !important; }
  .cluster-desc { color: #94a3b8 !important; }
  .cluster-index { color: #fbbf24 !important; background: rgba(245, 158, 11, 0.15) !important; }
}
</style>
