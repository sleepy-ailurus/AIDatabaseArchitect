<template>
  <div class="export-page">
    <div class="export-header">
      <div class="header-left">
        <el-button text @click="$router.back()">
          <el-icon style="margin-right: 4px;"><ArrowLeft /></el-icon>返回 ER 编辑器
        </el-button>
        <el-divider direction="vertical" />
        <div>
          <h2 class="title">数据库设计文档导出</h2>
          <p class="subtitle">
            {{ docMeta.project_name || '数据库设计文档' }}
            <template v-if="docMeta.generated_at"> · 生成时间: {{ formatTime(docMeta.generated_at) }}</template>
            <template v-if="docMeta.version"> · 版本 {{ docMeta.version }}</template>
          </p>
        </div>
      </div>

      <div class="header-actions">
        <el-radio-group v-model="previewFormat" @change="onFormatChange">
          <el-radio-button value="markdown">Markdown</el-radio-button>
          <el-radio-button value="html">HTML</el-radio-button>
          <el-radio-button value="pdf" disabled>
            PDF <el-tag size="small" type="info" style="margin-left: 4px;">即将支持</el-tag>
          </el-radio-button>
        </el-radio-group>

        <el-divider direction="vertical" />

        <el-dropdown trigger="click" @command="onDownload">
          <el-button type="primary" :icon="Download" :loading="downloading">
            下载文档 <el-icon style="margin-left: 2px;"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="markdown"><el-icon><Document /></el-icon> Markdown (.md)</el-dropdown-item>
              <el-dropdown-item command="html"><el-icon><Monitor /></el-icon> HTML 单页 (.html)</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <el-button :icon="Refresh" :loading="loading" @click="loadPreview">刷新预览</el-button>
      </div>
    </div>

    <div class="export-body" v-loading="loading">
      <aside class="doc-toc">
        <div class="toc-head">
          <span style="font-size: 13px; font-weight: 600;">文档目录</span>
          <el-tooltip content="生成内容配置">
            <el-button text circle size="small" @click="showConfig = true">
              <el-icon><Setting /></el-icon>
            </el-button>
          </el-tooltip>
        </div>

        <el-scrollbar class="toc-scroll">
          <el-tree
            :data="tocData"
            node-key="id"
            default-expand-all
            :expand-on-click-node="false"
            :current-node-key="currentSection"
            @node-click="scrollToSection"
            class="toc-tree"
          >
            <template #default="{ node, data }">
              <div class="toc-node">
                <span class="node-num" v-if="data.num">{{ data.num }}</span>
                <span class="node-label">{{ node.label }}</span>
                <el-tag v-if="data.count" size="small" effect="plain" round>
                  {{ data.count }}
                </el-tag>
              </div>
            </template>
          </el-tree>
        </el-scrollbar>

        <div class="toc-foot">
          <div class="doc-stats">
            <div class="stat-row">
              <span>文档大小</span><strong>{{ docStats.size || '-' }}</strong>
            </div>
            <div class="stat-row">
              <span>表数量</span><strong>{{ docStats.table_count || 0 }}</strong>
            </div>
            <div class="stat-row">
              <span>关系数</span><strong>{{ docStats.relation_count || 0 }}</strong>
            </div>
            <div class="stat-row">
              <span>章节数</span><strong>{{ tocData.length }}</strong>
            </div>
          </div>
        </div>
      </aside>

      <main class="doc-preview">
        <el-scrollbar ref="docScroll">
          <div class="md-content" v-if="previewHtml" v-html="previewHtml"></div>
          <div class="md-content" v-else-if="previewText">
            <pre class="raw-md">{{ previewText }}</pre>
          </div>
          <el-empty v-else-if="!loading" description="暂无文档预览，请点击刷新预览生成">
            <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadPreview">生成预览</el-button>
          </el-empty>
        </el-scrollbar>
      </main>
    </div>

    <el-dialog v-model="showConfig" title="生成内容配置" width="480px">
      <el-form label-width="120px">
        <el-form-item label="文档格式">
          <el-radio-group v-model="config.format">
            <el-radio value="markdown">Markdown</el-radio>
            <el-radio value="html">HTML</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="包含章节">
          <el-checkbox-group v-model="config.sections">
            <el-checkbox value="overview">数据库概述</el-checkbox>
            <el-checkbox value="er_diagram">ER 关系图</el-checkbox>
            <el-checkbox value="tables">表结构说明</el-checkbox>
            <el-checkbox value="relations">关系与索引</el-checkbox>
            <el-checkbox value="ai_relations">AI 推断说明</el-checkbox>
            <el-checkbox value="quality">质量建议</el-checkbox>
            <el-checkbox value="version">版本记录</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="包含 AI 关系">
          <el-switch v-model="config.include_ai" />
        </el-form-item>
        <el-form-item label="表结构展开">
          <el-switch v-model="config.expand_columns" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConfig = false">取消</el-button>
        <el-button type="primary" @click="applyConfig">应用并重新生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { exportDocument, previewDocument, getExport } from '@/api/export'

const route = useRoute()
const projectId = computed(() => route.params.id)

const previewFormat = ref('markdown')
const currentSection = ref(1)
const docScroll = ref()
const loading = ref(false)
const downloading = ref(false)
const showConfig = ref(false)
const previewText = ref('')
const previewHtml = ref('')

const docMeta = reactive({
  project_name: '',
  generated_at: '',
  version: '',
  database_name: '',
  database_version: '',
  charset: ''
})

const docStats = reactive({
  size: '-',
  table_count: 0,
  relation_count: 0,
  ai_relation_count: 0,
  field_count: 0
})

const config = reactive({
  format: 'markdown',
  sections: ['overview', 'er_diagram', 'tables', 'relations', 'ai_relations', 'quality', 'version'],
  include_ai: true,
  expand_columns: true
})

const tocData = computed(() => {
  const sections = config.sections
  const result = []
  let num = 1
  if (sections.includes('overview')) {
    result.push({ id: 'overview', num: String(num++), label: '数据库概述', children: [
      { id: 'overview-basic', num: `${num - 1}.1`, label: '基本信息' },
      { id: 'overview-stats', num: `${num - 1}.2`, label: '数据概览' }
    ]})
  }
  if (sections.includes('er_diagram')) {
    result.push({ id: 'er_diagram', num: String(num++), label: 'ER 关系图' })
  }
  if (sections.includes('tables')) {
    result.push({ id: 'tables', num: String(num++), label: '表结构说明', count: `${docStats.table_count} 张` })
  }
  if (sections.includes('relations')) {
    result.push({ id: 'relations', num: String(num++), label: '关系与索引说明', count: `${docStats.relation_count} 条` })
  }
  if (sections.includes('ai_relations') && config.include_ai) {
    result.push({ id: 'ai_relations', num: String(num++), label: 'AI 推断说明', count: `${docStats.ai_relation_count} 条` })
  }
  if (sections.includes('quality')) {
    result.push({ id: 'quality', num: String(num++), label: '数据库质量建议' })
  }
  if (sections.includes('version')) {
    result.push({ id: 'version', num: String(num++), label: '附录：版本记录' })
  }
  return result
})

const formatTime = (t) => {
  if (!t) return ''
  return dayjs(t).format('YYYY-MM-DD HH:mm:ss')
}

const renderPreview = (data) => {
  if (!data) {
    previewText.value = ''
    previewHtml.value = ''
    return
  }
  const content = typeof data === 'string' ? data
    : data.content || data.markdown || data.html || data.text || ''
  const fmt = data.format || config.format

  if (fmt === 'html' || (typeof content === 'string' && content.trim().startsWith('<'))) {
    previewHtml.value = content
    previewText.value = ''
  } else {
    previewText.value = content
    previewHtml.value = ''
  }

  const meta = data.meta || data.metadata || {}
  Object.assign(docMeta, {
    project_name: meta.project_name || data.project_name || '',
    generated_at: meta.generated_at || data.generated_at || '',
    version: meta.version || data.version || '',
    database_name: meta.database_name || data.database_name || '',
    database_version: meta.database_version || data.database_version || '',
    charset: meta.charset || data.charset || ''
  })
  const stats = data.stats || data.statistics || {}
  Object.assign(docStats, {
    size: stats.size || data.size || '-',
    table_count: stats.table_count ?? data.table_count ?? 0,
    relation_count: stats.relation_count ?? data.relation_count ?? 0,
    ai_relation_count: stats.ai_relation_count ?? data.ai_relation_count ?? 0,
    field_count: stats.field_count ?? data.field_count ?? 0
  })
}

const loadPreview = async () => {
  loading.value = true
  try {
    const payload = {
      format: previewFormat.value,
      sections: config.sections,
      include_ai: config.include_ai,
      expand_columns: config.expand_columns
    }
    const data = await previewDocument(projectId.value, payload)
    renderPreview(data)
  } catch (e) {
    ElMessage.error('生成预览失败，请检查后端服务')
    previewText.value = ''
    previewHtml.value = ''
  } finally {
    loading.value = false
  }
}

const onFormatChange = () => {
  config.format = previewFormat.value
  loadPreview()
}

const applyConfig = () => {
  showConfig.value = false
  previewFormat.value = config.format
  loadPreview()
}

const onDownload = async (format) => {
  downloading.value = true
  try {
    const payload = {
      format,
      sections: config.sections,
      include_ai: config.include_ai,
      expand_columns: config.expand_columns
    }
    const blob = await exportDocument(projectId.value, payload)
    const ext = format === 'html' ? 'html' : 'md'
    const filename = `${docMeta.project_name || 'database-design'}.${ext}`
    const url = window.URL.createObjectURL(new Blob([blob]))
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('文档下载已开始')
  } catch (e) {
    ElMessage.error('下载失败，请检查后端服务')
  } finally {
    downloading.value = false
  }
}

const scrollToSection = (node) => {
  currentSection.value = node.id
  const el = document.getElementById(`sec-${node.id}`)
  if (el && docScroll.value) {
    const wrap = docScroll.value.wrapRef
    if (wrap) {
      wrap.scrollTo({ top: el.offsetTop - 20, behavior: 'smooth' })
    }
  }
}

onMounted(() => {
  if (projectId.value) {
    loadPreview()
    getExport(projectId.value).catch(() => {})
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.export-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: $bg-color;
  overflow: hidden;
}

.export-header {
  background: $bg-white;
  padding: 14px 28px;
  border-bottom: 1px solid $border-light;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title {
  font-size: 18px;
  font-weight: 700;
  color: $text-primary;
  margin: 0;
}

.subtitle {
  font-size: 12px;
  color: $text-secondary;
  margin: 3px 0 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.export-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.doc-toc {
  width: 280px;
  background: $bg-white;
  border-right: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.toc-head {
  padding: 16px 20px;
  border-bottom: 1px solid $border-light;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toc-scroll {
  flex: 1;
  padding: 8px 10px;
}

.toc-tree {
  background: transparent;

  :deep(.el-tree-node__content) {
    height: 36px;
    border-radius: 6px;
    margin-bottom: 2px;
    padding-left: 0 !important;
  }

  :deep(.el-tree-node__content:hover) {
    background: $bg-light;
  }

  :deep(.is-current > .el-tree-node__content) {
    background: rgba(59, 130, 246, 0.08);

    .node-label { color: $primary-color; font-weight: 600; }
    .node-num { background: $primary-color; color: white; }
  }
}

.toc-node {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: $text-regular;
  width: 100%;
}

.node-num {
  min-width: 22px;
  height: 20px;
  padding: 0 6px;
  background: #F1F5F9;
  color: $text-secondary;
  font-size: 10px;
  font-weight: 700;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-label {
  flex: 1;
  font-weight: 500;
}

.toc-foot {
  padding: 16px;
  border-top: 1px solid $border-light;
  background: $bg-light;
}

.doc-stats {
  .stat-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 12px;

    span { color: $text-secondary; }
    strong { color: $text-primary; font-weight: 600; }
  }
}

.doc-preview {
  flex: 1;
  overflow: hidden;
  min-width: 0;
  background: #E5E7EB;
  padding: 20px 40px;

  :deep(.el-scrollbar__wrap) {
    border-radius: $radius-lg;
  }
}

.md-content {
  max-width: 960px;
  margin: 0 auto;
  background: white;
  border-radius: $radius-lg;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  padding: 28px 40px;
  min-height: 400px;

  :deep(h1) {
    font-size: 26px;
    font-weight: 800;
    color: $text-primary;
    margin: 0 0 16px;
  }

  :deep(h2) {
    font-size: 20px;
    font-weight: 700;
    color: $text-primary;
    margin: 24px 0 14px;
    padding-bottom: 10px;
    border-bottom: 2px solid $primary-color;
    display: inline-block;
  }

  :deep(h3) {
    font-size: 15px;
    font-weight: 700;
    color: $text-primary;
    margin: 22px 0 10px;
  }

  :deep(p) {
    font-size: 13px;
    line-height: 1.8;
    color: $text-regular;
    margin: 8px 0;

    code {
      font-family: 'SF Mono', Consolas, monospace;
      background: #F1F5F9;
      padding: 1px 5px;
      border-radius: 3px;
      font-size: 12px;
      color: #4338CA;
    }
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 12px;

    th {
      padding: 10px 12px;
      text-align: left;
      font-weight: 600;
      color: $text-regular;
      font-size: 11px;
      background: #F8FAFC;
      border-bottom: 1px solid $border-light;
    }

    td {
      padding: 9px 12px;
      border-bottom: 1px solid $border-light;
      color: $text-regular;
    }

    tr:last-child td {
      border-bottom: none;
    }
  }

  :deep(code) {
    font-family: 'SF Mono', Consolas, monospace;
    font-size: 12px;
  }

  :deep(pre) {
    background: #0F172A;
    color: #E2E8F0;
    padding: 14px 18px;
    border-radius: $radius-md;
    overflow: auto;

    code {
      font-family: 'SF Mono', Consolas, monospace;
      font-size: 12px;
      line-height: 1.7;
      color: #E2E8F0;
    }
  }
}

.raw-md {
  background: #0F172A;
  color: #E2E8F0;
  padding: 18px;
  border-radius: $radius-md;
  overflow: auto;
  font-family: 'SF Mono', Consolas, monospace;
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
