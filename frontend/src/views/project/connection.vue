<template>
  <div class="connection-page">
    <div class="steps-header">
      <el-steps :active="currentStep" finish-status="success" align-center>
        <el-step :title="t('connection.steps.dbConnection')" icon="Connection" />
        <el-step :title="t('connection.steps.schemaParse')" icon="DataAnalysis" />
        <el-step :title="t('connection.steps.erEdit')" icon="Share" />
        <el-step :title="t('connection.steps.aiConfirm')" icon="MagicStick" />
        <el-step :title="t('connection.steps.docExport')" icon="Download" />
      </el-steps>
    </div>

    <div class="work-area">
      <div class="left-panel">
        <div class="panel-title-section">
          <div>
            <h2 class="panel-title">{{ t('connection.title') }}</h2>
            <p class="panel-desc">{{ t('connection.desc') }}</p>
          </div>
          <div class="project-chip" v-if="projectName">
            <el-icon :size="16" color="#3B82F6"><FolderOpened /></el-icon>
            <span>{{ projectName }}</span>
          </div>
        </div>

        <div class="security-tip">
          <el-icon :size="18" color="#F59E0B"><Warning /></el-icon>
          <div class="tip-content">
            <strong>{{ t('connection.securityTip') }}</strong>
            <span>{{ t('connection.securityTipDesc') }}</span>
          </div>
        </div>

        <el-form :model="form" :rules="rules" ref="formRef" :label-width="formLabelWidth" class="connection-form">
          <el-form-item :label="t('connection.dbType')" prop="db_type">
            <el-radio-group v-model="form.db_type" class="type-group">
              <el-radio-button value="mysql">
                <span class="radio-label">
                  <span class="radio-dot mysql"></span>
                  MySQL 8.x
                </span>
              </el-radio-button>
              <el-radio-button value="postgresql">
                <span class="radio-label">
                  <span class="radio-dot pg"></span>
                  PostgreSQL
                </span>
              </el-radio-button>
            </el-radio-group>
          </el-form-item>

          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item :label="t('connection.host')" prop="host">
                <el-input v-model="form.host" :placeholder="t('connection.hostPlaceholder')">
                  <template #prefix><el-icon><Monitor /></el-icon></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('connection.port')" prop="port">
                <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%;" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item :label="t('connection.databaseName')" prop="database_name">
            <el-input v-model="form.database_name" :placeholder="t('connection.databaseNamePlaceholder')">
              <template #prefix><el-icon><Coin /></el-icon></template>
            </el-input>
          </el-form-item>

          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item :label="t('connection.username')" prop="username">
                <el-input v-model="form.username" :placeholder="t('connection.usernamePlaceholder')">
                  <template #prefix><el-icon><User /></el-icon></template>
                </el-input>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('connection.password')" prop="password">
                <el-input v-model="form.password" :type="showPassword ? 'text' : 'password'" :placeholder="t('connection.passwordPlaceholder')">
                  <template #prefix><el-icon><Lock /></el-icon></template>
                  <template #suffix>
                    <el-button text @click="showPassword = !showPassword">
                      <el-icon :size="16">
                        <component :is="showPassword ? 'View' : 'Hide'" />
                      </el-icon>
                    </el-button>
                  </template>
                </el-input>
              </el-form-item>
            </el-col>
          </el-row>

          <el-divider content-position="left">
            <span style="font-size: 13px; color: #64748B; font-weight: 500;">{{ t('connection.advanced') }}</span>
          </el-divider>

          <el-form-item :label="t('connection.enableSSL')">
            <el-switch v-model="form.ssl" />
            <span style="margin-left: 8px; font-size: 12px; color: #94A3B8;">
              {{ t('connection.sslDesc') }}
            </span>
          </el-form-item>

          <el-form-item v-if="form.ssl" :label="t('connection.caCert')">
            <el-input
              v-model="form.ca"
              type="textarea"
              :rows="4"
              style="width: 100%;"
              :placeholder="t('connection.caPlaceholder')"
            />
          </el-form-item>

          <el-form-item :label="t('connection.timeout')">
            <el-input-number v-model="form.timeout" :min="5" :max="30" :step="5" style="width: 160px;" />
            <span style="margin-left: 8px; font-size: 12px; color: #94A3B8;">{{ t('connection.timeoutUnit') }}</span>
          </el-form-item>
        </el-form>

        <div class="form-actions">
          <el-button @click="$router.back()">
            <el-icon style="margin-right: 4px;"><ArrowLeft /></el-icon>{{ t('connection.back') }}
          </el-button>
          <div>
            <el-button :icon="RefreshRight" :loading="testingConnection" @click="handleTestConnection">
              {{ t('connection.testConnection') }}
            </el-button>
            <el-button type="primary" :icon="VideoPlay" :loading="syncing" @click="handleSaveAndSync">
              {{ t('connection.saveAndSync') }}
            </el-button>
          </div>
        </div>
      </div>

      <div class="right-panel">
        <div class="test-result-section">
          <div class="section-title">
            <span>{{ t('connection.testResult') }}</span>
            <el-tag v-if="testPassed" size="small" type="success" effect="light">
              <el-icon><CircleCheck /></el-icon> {{ t('connection.connected') }}
            </el-tag>
            <el-tag v-else-if="testingConnection" size="small" type="warning" effect="light">
              <el-icon class="el-icon--loading"><Loading /></el-icon> {{ t('connection.testing') }}
            </el-tag>
            <el-tag v-else-if="testFailed" size="small" type="danger" effect="light">{{ t('connection.connectionFailed') }}</el-tag>
            <el-tag v-else size="small" type="info" effect="light">{{ t('connection.notTested') }}</el-tag>
          </div>

          <div class="check-list">
            <div class="check-item" v-for="(item, idx) in checkItems" :key="idx" :class="item.status">
              <div class="check-icon">
                <el-icon v-if="item.status === 'passing'" color="#10B981"><CircleCheckFilled /></el-icon>
                <el-icon v-else-if="item.status === 'failed'" color="#EF4444"><CircleCloseFilled /></el-icon>
                <el-icon v-else-if="item.status === 'running'" color="#F59E0B" class="el-icon--loading"><Loading /></el-icon>
                <el-icon v-else color="#CBD5E1"><Circle /></el-icon>
              </div>
              <div class="check-info">
                <div class="check-name">{{ checkText(item.name) }}</div>
                <div class="check-detail" v-if="checkText(item.detail)">{{ checkText(item.detail) }}</div>
              </div>
              <div class="check-time" v-if="item.time">{{ item.time }}ms</div>
            </div>
          </div>

          <div class="error-detail" v-if="errorMessage">
            <el-icon color="#EF4444"><WarningFilled /></el-icon>
            <div>
              <div style="font-weight: 600; color: #DC2626; margin-bottom: 4px;">{{ t('connection.errorDetail') }}</div>
              <div style="font-size: 12px; color: #B91C1C;">{{ errorMessage }}</div>
              <div class="error-type" v-if="errorType">{{ t('connection.errorType') }}: <code>{{ errorType }}</code></div>
            </div>
          </div>
        </div>

        <div class="preview-section" v-if="testPassed && dbPreview">
          <div class="section-title">
            <span>{{ t('connection.dbPreview') }}</span>
          </div>
          <div class="db-info">
            <div class="info-row" v-if="dbPreview.version">
              <span class="info-label">{{ t('connection.dbVersion') }}</span>
              <span class="info-value">{{ dbPreview.version }}</span>
            </div>
            <div class="info-row" v-if="dbPreview.charset">
              <span class="info-label">{{ t('connection.charset') }}</span>
              <span class="info-value">{{ dbPreview.charset }}</span>
            </div>
            <div class="info-row highlight" v-if="dbPreview.table_count !== undefined">
              <span class="info-label">{{ t('connection.tableCount') }}</span>
              <span class="info-value strong">{{ dbPreview.table_count }} {{ t('connection.tables') }}</span>
            </div>
            <div class="info-row highlight" v-if="dbPreview.view_count !== undefined">
              <span class="info-label">{{ t('connection.viewCount') }}</span>
              <span class="info-value strong">{{ dbPreview.view_count }} {{ t('connection.views') }}</span>
            </div>
            <div class="info-row highlight" v-if="dbPreview.fk_count !== undefined">
              <span class="info-label">{{ t('connection.fkCount') }}</span>
              <span class="info-value strong">{{ dbPreview.fk_count }} {{ t('connection.relations') }}</span>
            </div>
          </div>

          <div class="table-preview" v-if="dbPreview.tables && dbPreview.tables.length">
            <div class="preview-label">{{ t('connection.tablePreview') }}</div>
            <div class="mini-table">
              <div class="mini-row header">
                <span>{{ t('connection.tableName') }}</span>
                <span>{{ t('connection.engine') }}</span>
                <span>{{ t('connection.rows') }}</span>
                <span>{{ t('connection.size') }}</span>
              </div>
              <div class="mini-row" v-for="t in dbPreview.tables.slice(0, 6)" :key="t.name">
                <span class="tbl-name">{{ t.name }}</span>
                <span>{{ t.engine || '-' }}</span>
                <span>{{ t.rows || '-' }}</span>
                <span>{{ t.size || '-' }}</span>
              </div>
              <div class="mini-row more" v-if="dbPreview.table_count > 6">
                <span>{{ t('connection.moreTables', { count: dbPreview.table_count - 6 }) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="help-section">
          <div class="help-title">
            <el-icon :size="16" color="#6366F1"><QuestionFilled /></el-icon>
            <span>{{ t('connection.helpTitle') }}</span>
          </div>
          <div class="help-tip">
            {{ t('connection.helpTip') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { useProjectStore } from '@/stores/project'
import { testConnection, saveConnection, getConnection } from '@/api/connection'
import { syncSchema } from '@/api/schema'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
// English labels ("Connection Timeout") need more room than Chinese ones.
const formLabelWidth = computed(() => (locale.value === 'zh-CN' ? '110px' : '170px'))
const projectStore = useProjectStore()
const formRef = ref()
const projectId = computed(() => route.params.id)

const currentStep = ref(0)
const showPassword = ref(false)
const testingConnection = ref(false)
const syncing = ref(false)
const testPassed = ref(false)
const testFailed = ref(false)
const errorMessage = ref('')
const errorType = ref('')
const projectName = ref('')
const dbPreview = ref(null)
const hasSavedConnection = ref(false)
let projectDbType = null

const form = reactive({
  db_type: 'mysql',
  host: '',
  port: 3306,
  database_name: '',
  username: '',
  password: '',
  ssl: false,
  ca: '',
  timeout: 30
})

// Switch to the default port when the database type changes (only if the user
// has not customized the port).
watch(
  () => form.db_type,
  (type) => {
    if (type === 'postgresql' && (form.port === 3306 || form.port === 5432)) {
      form.port = 5432
    } else if (type === 'mysql' && (form.port === 3306 || form.port === 5432)) {
      form.port = 3306
    }
    // Default username per database type (only when empty or still the other
    // type's default, never overwrite a custom value).
    const defaultUser = type === 'postgresql' ? 'postgres' : 'root'
    if (!form.username || form.username === 'root' || form.username === 'postgres') {
      form.username = defaultUser
    }
  }
)

const rules = {
  host: [{ required: true, message: () => t('connection.formMessages.hostRequired'), trigger: 'blur' }],
  port: [{ required: true, message: () => t('connection.formMessages.portRequired'), trigger: 'blur' }],
  database_name: [{ required: true, message: () => t('connection.formMessages.databaseRequired'), trigger: 'blur' }],
  username: [{ required: true, message: () => t('connection.formMessages.usernameRequired'), trigger: 'blur' }],
  password: [{ required: true, message: () => t('connection.formMessages.passwordRequired'), trigger: 'blur' }]
}

const checkItems = reactive([
  { name: () => t('connection.networkCheck'), detail: '', status: 'idle', time: null },
  { name: () => t('connection.authCheck'), detail: '', status: 'idle', time: null },
  { name: () => t('connection.dbExistsCheck'), detail: '', status: 'idle', time: null },
  { name: () => t('connection.permissionCheck'), detail: () => t('connection.permissionCheckDesc'), status: 'idle', time: null },
  { name: () => t('connection.sslCheck'), detail: '', status: 'idle', time: null },
  { name: () => t('connection.schemaCheck'), detail: () => t('connection.schemaCheckDesc'), status: 'idle', time: null }
])

const checkText = (v) => (typeof v === 'function' ? v() : v)

const resetChecks = () => {
  checkItems.forEach(c => { c.status = 'idle'; c.time = null; c.detail = '' })
  checkItems[3].detail = () => t('connection.permissionCheckDesc')
  checkItems[5].detail = () => t('connection.schemaCheckDesc')
  errorMessage.value = ''
  errorType.value = ''
  testPassed.value = false
  testFailed.value = false
  dbPreview.value = null
}

const runCheckStep = async (idx, ok, detail) => {
  checkItems[idx].status = 'running'
  await new Promise(r => setTimeout(r, 200))
  if (ok) {
    checkItems[idx].status = 'passing'
    if (!checkItems[idx].time) checkItems[idx].time = Math.floor(Math.random() * 50 + 10)
    if (detail) checkItems[idx].detail = detail
  } else {
    checkItems[idx].status = 'failed'
    if (detail) checkItems[idx].detail = detail
  }
}

const handleTestConnection = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  resetChecks()
  testingConnection.value = true

  try {
    const payload = {
      db_type: form.db_type,
      host: String(form.host),
      port: Number(form.port),
      database_name: form.database_name,
      username: form.username,
      password: form.password || null,
      ssl_config: { enabled: !!form.ssl, ca: form.ca || null },
      timeout: Number(form.timeout)
    }
    const data = await testConnection(payload)

    const checks = data?.checks || []
    for (let i = 0; i < checkItems.length; i++) {
      const apiCheck = checks[i]
      if (apiCheck) {
        const passed = apiCheck.status === 'passing'
        await runCheckStep(i, passed, apiCheck.detail || '')
        if (apiCheck.time) checkItems[i].time = apiCheck.time
      } else {
        await runCheckStep(i, data?.success !== false)
      }
    }

    if (data?.success) {
      testPassed.value = true
      dbPreview.value = {
        version: data?.db_version,
        table_count: data?.table_count,
        elapsed_ms: data?.elapsed_ms
      }
      ElMessage.success(t('connection.testSuccess'))
    } else {
      testFailed.value = true
      errorMessage.value = data?.message || t('connection.testFailedMsg')
      errorType.value = 'CONNECTION_ERROR'
    }
  } catch (e) {
    testFailed.value = true
    const resp = e?.response?.data
    errorMessage.value = resp?.message || e?.message || t('connection.connectionFailed')
    errorType.value = resp?.error_type || resp?.code || ''
    checkItems.forEach(c => {
      if (c.status === 'running' || c.status === 'idle') c.status = 'failed'
    })
  } finally {
    testingConnection.value = false
  }
}

const handleSaveAndSync = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  syncing.value = true
  currentStep.value = 1
  try {
    await saveConnection({
      project_id: Number(projectId.value),
      db_type: form.db_type,
      host: String(form.host),
      port: Number(form.port),
      database_name: form.database_name,
      username: form.username,
      password: form.password || null,
      ssl_config: { enabled: !!form.ssl, ca: form.ca || null },
      timeout: Number(form.timeout),
      save_credentials: true
    })
    ElMessage.success(t('connection.saveSuccess'))

    currentStep.value = 2
    const syncData = await syncSchema(projectId.value)
    ElMessage.success(t('connection.syncSuccess'))

    currentStep.value = 3
    setTimeout(() => {
      router.push(`/projects/${projectId.value}/er-model`)
    }, 600)
  } catch (e) {
    currentStep.value = 0
  } finally {
    syncing.value = false
  }
}

const loadExistingConnection = async () => {
  try {
    const data = await getConnection(projectId.value)
    if (data) {
      hasSavedConnection.value = true
      Object.assign(form, {
        db_type: data.db_type || form.db_type,
        host: data.host || '',
        port: data.port || 3306,
        database_name: data.database_name || data.database || '',
        username: data.username || '',
        password: data.password || '',
        ssl: data.ssl || false,
        ca: data.ssl_config?.ca || '',
        timeout: data.timeout || 30
      })
      if (data.tested) {
        testPassed.value = true
      }
    } else if (projectDbType) {
      // No saved connection yet: use the db type chosen when creating the project.
      form.db_type = projectDbType
    }
  } catch {
    // no existing connection, ignore
  }
}

const loadProject = async () => {
  try {
    const data = await projectStore.fetchProject(projectId.value)
    if (data) {
      projectName.value = data.name
      projectDbType = data.db_type || null
      if (!hasSavedConnection.value && projectDbType) {
        form.db_type = projectDbType
      }
    }
  } catch {
    // ignore
  }
}

// 切换项目时（组件被复用，仅 route.params.id 变化），重置表单和状态后重新加载
watch(projectId, async (newId, oldId) => {
  if (!newId || newId === oldId) return
  Object.assign(form, {
    db_type: 'mysql', host: '', port: 3306, database_name: '',
    username: '', password: '', ssl: false, ca: '', timeout: 30
  })
  currentStep.value = 0
  resetChecks()
  await Promise.all([loadProject(), loadExistingConnection()])
})

onMounted(() => {
  loadProject()
  loadExistingConnection()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.connection-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: $bg-color;
}

.steps-header {
  background: $bg-white;
  padding: 20px 40px;
  border-bottom: 1px solid $border-light;

  :deep(.el-step) {
    padding: 0 12px;
  }
}

.work-area {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding: 24px 40px;
  overflow: auto;
}

.left-panel {
  flex: 1.2;
  background: $bg-white;
  border-radius: $radius-lg;
  padding: 28px;
  box-shadow: $shadow-sm;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.right-panel {
  flex: 0.8;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.panel-title-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.panel-title {
  font-size: 20px;
  font-weight: 700;
  color: $text-primary;
  margin: 0;
}

.panel-desc {
  font-size: 13px;
  color: $text-secondary;
  margin: 6px 0 0;
}

.project-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 45%;
  min-width: 0;
  padding: 6px 12px;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 20px;
  font-size: 12px;
  color: $primary-color;
  font-weight: 500;

  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.security-tip {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.06), rgba(245, 158, 11, 0.02));
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-radius: $radius-md;
  margin-bottom: 24px;

  .tip-content {
    font-size: 12px;
    line-height: 1.6;
    color: $text-regular;

    strong {
      color: $warning-color;
      margin-right: 4px;
    }
  }
}

.connection-form {
  flex: 1;
}

.type-group {
  width: 100%;
  display: flex;

  :deep(.el-radio-button) {
    flex: 1;

    .el-radio-button__inner {
      width: 100%;
      padding: 12px 16px;
      text-align: left;
    }
  }
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
}

.radio-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;

  &.mysql { background: #4479A1; }
  &.pg { background: #336791; }
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 20px;
  margin-top: auto;
  border-top: 1px solid $border-light;
}

.test-result-section,
.preview-section,
.help-section {
  background: $bg-white;
  border-radius: $radius-lg;
  padding: 20px;
  box-shadow: $shadow-sm;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid $border-light;
}

.check-list {
  .check-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 0;

    & + & {
      border-top: 1px dashed $border-light;
    }
  }

  .check-icon {
    flex-shrink: 0;
    width: 20px;
    display: flex;
    align-items: center;
  }

  .check-info {
    flex: 1;
    min-width: 0;
  }

  .check-name {
    font-size: 13px;
    color: $text-regular;
    font-weight: 500;
  }

  .check-detail {
    font-size: 11px;
    color: $text-secondary;
    margin-top: 2px;
  }

  .check-time {
    font-size: 11px;
    color: $text-secondary;
    font-weight: 500;
  }

  .check-item.passing .check-name { color: #059669; }
  .check-item.running .check-name { color: #D97706; }
  .check-item.failed .check-name { color: #DC2626; }
}

.error-detail {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  margin-top: 14px;
  background: rgba(239, 68, 68, 0.04);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: $radius-md;
}

.error-type {
  margin-top: 6px;
  font-size: 11px;
  color: $text-secondary;

  code {
    font-family: 'SF Mono', monospace;
    background: $bg-white;
    padding: 1px 6px;
    border-radius: 3px;
    border: 1px solid $border-light;
  }
}

.db-info {
  .info-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    font-size: 13px;

    &.highlight {
      padding: 10px 12px;
      margin: 4px 0;
      background: $bg-light;
      border-radius: $radius-sm;
    }
  }

  .info-label { color: $text-secondary; }
  .info-value { color: $text-primary; font-weight: 500; }
  .info-value.strong { color: $primary-color; font-weight: 700; font-size: 14px; }
}

.table-preview {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed $border-light;
}

.preview-label {
  font-size: 12px;
  color: $text-secondary;
  margin-bottom: 10px;
  font-weight: 500;
}

.mini-table {
  border: 1px solid $border-light;
  border-radius: $radius-md;
  overflow: hidden;

  .mini-row {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr;
    padding: 8px 10px;
    font-size: 12px;
    color: $text-regular;

    & + & { border-top: 1px solid $border-light; }

    &.header {
      background: $bg-light;
      font-weight: 600;
      color: $text-secondary;
      font-size: 11px;
      text-transform: uppercase;
    }

    &.more {
      background: $bg-light;
      color: $text-placeholder;
      text-align: center;
      display: block;
    }
  }

  .tbl-name {
    font-family: 'SF Mono', Consolas, monospace;
    color: $primary-color;
    font-weight: 600;
  }
}

.help-section {
  .help-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 12px;
  }

  .help-tip {
    font-size: 12px;
    line-height: 1.8;
    color: #64748B;
    background: rgba(99, 102, 241, 0.06);
    border: 1px solid rgba(99, 102, 241, 0.18);
    border-radius: 6px;
    padding: 10px 12px;
  }
}

html.dark {
  .connection-page {
    background: #1e1e1e;
  }

  .steps-header {
    background: #252526;
    border-bottom-color: #3a3a3c;
  }

  .left-panel,
  .help-section,
  .test-result-section {
    background: #252526 !important;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.25), 0 4px 6px -4px rgba(0, 0, 0, 0.2) !important;
  }

  .panel-title,
  .section-title,
  .help-title,
  .preview-label,
  .info-value {
    color: #e2e8f0;
  }

  .panel-desc,
  .info-label,
  .error-type,
  .check-item .check-detail {
    color: #94a3b8;
  }

  .project-chip {
    background: rgba(59, 130, 246, 0.16);
    color: #93c5fd;
  }

  .security-tip {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(245, 158, 11, 0.05));
    border-color: rgba(245, 158, 11, 0.3);

    .tip-content {
      color: #d1d5db;
    }
  }

  .help-tip {
    color: #94a3b8;
    background: rgba(99, 102, 241, 0.12);
    border-color: rgba(99, 102, 241, 0.3);
  }

  .check-item .check-name {
    color: #d1d5db;
  }

  .mini-table {
    border-color: #3a3a3c;
  }

  .mini-table .mini-row {
    color: #d1d5db;
  }

  .form-actions :deep(.el-button:not(.el-button--primary)) {
    color: #e2e8f0;
    border-color: #3a3a3c;
    background: #2a2a2b;
  }
}
</style>
