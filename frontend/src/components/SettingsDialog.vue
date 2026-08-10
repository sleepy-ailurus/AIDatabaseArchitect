<template>
  <div class="settings-root">
    <div class="settings-header">
      <el-icon :size="22" color="#3B82F6"><Setting /></el-icon>
      <span class="settings-title">{{ t('settings.title') }}</span>
    </div>

    <div class="settings-body">
      <aside class="settings-nav">
        <div
          v-for="item in navItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: activeNav === item.key }"
          @click="activeNav = item.key"
        >
          <el-icon :size="16">
            <component :is="item.icon" />
          </el-icon>
          <span>{{ t(`settings.nav.${item.key}`) }}</span>
        </div>
      </aside>

      <div class="settings-content">
        <template v-if="activeNav === 'general'">
          <div class="content-header">
            <h3>{{ t('settings.general.title') }}</h3>
            <p>{{ t('settings.general.desc') }}</p>
          </div>
          <div class="config-section">
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">{{ t('settings.general.theme') }}</div>
                <div class="config-desc">{{ t('settings.general.themeDesc') }}</div>
              </div>
              <el-radio-group :model-value="settingsStore.theme" @change="settingsStore.setTheme">
                <el-radio-button value="light">{{ t('settings.general.light') }}</el-radio-button>
                <el-radio-button value="dark">{{ t('settings.general.dark') }}</el-radio-button>
                <el-radio-button value="auto">{{ t('settings.general.auto') }}</el-radio-button>
              </el-radio-group>
            </div>
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">{{ t('settings.general.language') }}</div>
                <div class="config-desc">{{ t('settings.general.languageDesc') }}</div>
              </div>
              <el-select :model-value="settingsStore.language" style="width: 160px;" @change="settingsStore.setLanguage">
                <el-option :label="t('settings.general.zhCN')" value="zh-CN" />
                <el-option :label="t('settings.general.enUS')" value="en-US" />
              </el-select>
            </div>
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">{{ t('settings.general.autoSave') }}</div>
                <div class="config-desc">{{ t('settings.general.autoSaveDesc') }}</div>
              </div>
              <el-switch v-model="general.autoSave" />
            </div>
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">{{ t('settings.general.showConfidence') }}</div>
                <div class="config-desc">{{ t('settings.general.showConfidenceDesc') }}</div>
              </div>
              <el-switch v-model="general.showConfidence" />
            </div>
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">{{ t('settings.general.autoCheckHigh') }}</div>
                <div class="config-desc">{{ t('settings.general.autoCheckHighDesc') }}</div>
              </div>
              <el-switch v-model="general.autoCheckHigh" />
            </div>
          </div>
        </template>

        <template v-if="activeNav === 'models'">
          <div class="content-header">
            <h3>{{ t('settings.nav.models') }}</h3>
          </div>

          <div class="models-wrapper" v-loading="loadingConfigs">
            <div class="provider-list">
              <transition-group name="list" tag="div" class="cards">
                <div
                  v-for="provider in providers"
                  :key="provider.id"
                  class="provider-card"
                  :class="{ expanded: expandedId === provider.id }"
                >
                  <div class="card-header" @click="toggleExpand(provider.id)">
                    <div class="card-header-left">
                      <span class="drag-handle">⋮⋮</span>
                      <el-radio
                        :model-value="activeProviderId"
                        :label="provider.id"
                        @change="activeProviderId = provider.id; selectProvider(provider)"
                        @click.stop
                      />
                      <span class="provider-name">{{ provider.name || t('llm.provider.namePlaceholder') }}</span>
                    </div>
                    <div class="card-header-right">
                      <el-switch
                        v-model="provider.enabled"
                        @click.stop
                        class="mini-switch"
                      />
                      <el-icon
                        class="action-icon delete"
                        @click.stop="deleteProvider(provider.id)"
                      >
                        <Delete />
                      </el-icon>
                      <el-icon
                        class="action-icon expand-arrow"
                        :class="{ rotated: expandedId === provider.id }"
                      >
                        <ArrowDown />
                      </el-icon>
                    </div>
                  </div>

                  <div class="card-body" v-show="expandedId === provider.id">
                    <div class="body-section">
                      <div class="field-label">{{ t('llm.provider.name') }}</div>
                      <el-input v-model="provider.name" :placeholder="t('llm.provider.namePlaceholder')" />
                    </div>

                    <div class="body-section">
                      <el-collapse v-model="activeCollapse" class="curl-collapse">
                        <el-collapse-item name="curl">
                          <template #title>
                            <span class="curl-title">
                              <el-icon><Promotion /></el-icon>
                              {{ t('llm.provider.curlImport') }}
                            </span>
                          </template>
                          <div class="curl-import">
                            <el-input
                              v-model="curlText"
                              type="textarea"
                              :rows="4"
                              :placeholder="t('llm.provider.curlPlaceholder')"
                            />
                            <el-button type="primary" size="small" @click="importFromCurl(provider)">{{ t('llm.provider.import') }}</el-button>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>

                    <div class="body-section">
                      <div class="field-label">{{ t('llm.provider.protocol') }}</div>
                      <div class="protocol-tabs">
                        <div
                          v-for="p in protocols"
                          :key="p"
                          class="protocol-tab"
                          :class="{ active: provider.protocol === p }"
                          @click="provider.protocol = p"
                        >{{ p }}</div>
                      </div>
                    </div>

                    <div class="body-section">
                      <el-collapse v-model="activeCollapse2" class="ref-collapse">
                        <el-collapse-item name="ref">
                          <template #title>
                            <span class="ref-title">
                              <el-icon><Document /></el-icon>
                              {{ t('llm.provider.endpoint') }} ({{ provider.protocol }})
                            </span>
                          </template>
                          <div class="ref-config">
                            <div class="ref-endpoint">
                              <span class="ref-label">{{ t('llm.provider.endpoint') }}:</span>
                              <el-radio-group v-model="provider.endpoint_path" size="small">
                                <el-radio-button value="/chat/completions">/chat/completions</el-radio-button>
                                <el-radio-button value="/responses">/responses</el-radio-button>
                              </el-radio-group>
                            </div>
                            <div class="ref-url">
                              <div class="ref-label">{{ t('llm.provider.baseUrl') }}</div>
                              <el-input v-model="provider.base_url" />
                              <div class="preset-tags">
                                <span
                                  v-for="tag in presetUrls"
                                  :key="tag.label"
                                  class="preset-tag"
                                  :class="{ active: provider.base_url === tag.value }"
                                  @click="provider.base_url = tag.value"
                                >{{ tag.label }}</span>
                              </div>
                            </div>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>

                    <div class="body-section">
                      <div class="field-label">{{ t('llm.provider.apiKey') }}</div>
                      <div class="key-input-wrap">
                        <el-input
                          v-model="provider.api_key"
                          :type="showKeyMap[provider.id] ? 'text' : 'password'"
                          :placeholder="t('llm.provider.apiKey')"
                        />
                        <el-icon
                          class="key-toggle"
                          @click="toggleKeyVisibility(provider.id)"
                        >
                          <View v-if="showKeyMap[provider.id]" />
                          <Hide v-else />
                        </el-icon>
                      </div>
                    </div>

                    <div class="body-section inline-fields">
                      <div class="inline-field">
                        <div class="field-label">{{ t('llm.provider.timeout') }}</div>
                        <div class="timeout-input">
                          <el-input-number
                            v-model="provider.timeout"
                            :min="1"
                            :max="600"
                            controls-position="right"
                          />
                          <span class="unit">{{ t('llm.provider.timeoutDesc') }}</span>
                        </div>
                      </div>
                    </div>

                    <div class="body-section">
                      <div class="rate-limit-row">
                        <div class="rate-limit-left">
                          <el-checkbox v-model="provider.rateUnlimited">{{ t('llm.provider.unlimited') }}</el-checkbox>
                        </div>
                        <div class="rate-limit-right" v-if="!provider.rateUnlimited">
                          <el-slider
                            v-model="provider.rateLimit"
                            :min="1"
                            :max="200"
                            :step="1"
                            class="rate-slider"
                          />
                          <span class="rate-value">{{ provider.rateLimit }}</span>
                          <span class="rate-unit">req/s</span>
                        </div>
                        <div v-else class="rate-value-unlimited">0</div>
                      </div>
                      <div class="field-label rate-label">{{ t('llm.provider.rateLimitDesc') }}</div>
                    </div>

                    <div class="body-section">
                      <div class="field-label">{{ t('llm.provider.models') }}</div>
                      <div class="model-input-row">
                        <el-input
                          v-model="provider.newModel"
                          :placeholder="t('llm.provider.modelPlaceholder')"
                          @keyup.enter="addModel(provider)"
                        />
                        <el-button
                          type="primary"
                          :icon="Plus"
                          @click="addModel(provider)"
                        >{{ t('llm.provider.addModel') }}</el-button>
                      </div>
                      <div class="model-tags" v-if="provider.models.length">
                        <el-tag
                          v-for="(m, idx) in provider.models"
                          :key="idx"
                          closable
                          class="model-tag"
                          @close="removeModel(provider, idx)"
                        >{{ m }}</el-tag>
                      </div>
                    </div>

                    <div class="body-section provider-actions">
                      <el-button
                        :icon="Connection"
                        :loading="provider._testing"
                        @click="testProvider(provider)"
                      >{{ t('llm.provider.testConnection') }}</el-button>
                      <el-button
                        type="primary"
                        :icon="Check"
                        :loading="provider._saving"
                        @click="saveProvider(provider)"
                      >{{ provider.id && !provider._isNew ? t('llm.provider.saveConfig') : t('llm.provider.createConfig') }}</el-button>
                      <el-tag
                        v-if="provider._testResult"
                        :type="provider._testResult.ok ? 'success' : 'danger'"
                        size="small"
                        effect="light"
                      >
                        {{ provider._testResult.ok ? t('llm.provider.connected') : t('llm.provider.connectFailed') }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </transition-group>

              <div class="add-provider-btn" @click="addProvider">
                <el-icon :size="18"><Plus /></el-icon>
                <span>{{ t('settings.llm.addProvider') }}</span>
              </div>
            </div>
          </div>
        </template>

        <template v-if="activeNav === 'shortcuts'">
          <div class="content-header">
            <h3>{{ t('settings.nav.shortcuts') }}</h3>
            <p>{{ t('settings.desc') }}</p>
          </div>
          <div class="shortcut-list">
            <div v-for="s in shortcuts" :key="s.name" class="shortcut-row">
              <span class="s-name">{{ t(`settings.shortcuts.${s.key}`) }}</span>
              <el-input v-model="s.keys" size="small" style="width: 200px;" />
            </div>
          </div>
        </template>

        <template v-if="activeNav === 'about'">
          <div class="content-header">
            <h3>{{ t('settings.nav.about') }}</h3>
          </div>
          <div class="about-section">
            <div class="about-logo">
              <el-icon :size="40" color="#3B82F6"><DataBase /></el-icon>
            </div>
            <div class="about-name">AI Database Architect</div>
            <div class="about-version">{{ t('settings.about.version') }}</div>
            <div class="about-desc">
              {{ t('settings.about.desc') }}
            </div>
            <div class="about-links">
              <el-button text type="primary" size="small"><el-icon><Link /></el-icon> {{ t('settings.about.docs') }}</el-button>
              <el-button text type="primary" size="small"><el-icon><ChatDotRound /></el-icon> {{ t('settings.about.feedback') }}</el-button>
              <el-button text type="primary" size="small"><el-icon><InfoFilled /></el-icon> {{ t('settings.about.changelog') }}</el-button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="settings-footer">
      <el-button @click="$emit('close')">{{ t('settings.buttons.close') }}</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLLMConfigs, saveLLMConfig, deleteLLMConfig, testLLMConfig, updateLLMConfig } from '@/api/llm'
import { useSettingsStore } from '@/stores/settings'

const { t } = useI18n()
defineEmits(['close'])

const settingsStore = useSettingsStore()

const activeNav = ref('general')
const expandedId = ref(null)
const activeProviderId = ref(null)
const activeCollapse = ref([])
const activeCollapse2 = ref([])
const curlText = ref('')
const loadingConfigs = ref(false)

const navItems = [
  { key: 'general', label: '通用配置', icon: 'Tools' },
  { key: 'models', label: '模型配置', icon: 'Cpu' },
  { key: 'shortcuts', label: '快捷键', icon: 'Key' },
  { key: 'about', label: '关于', icon: 'InfoFilled' }
]

const general = reactive({
  theme: 'auto',
  language: 'zh-CN',
  autoSave: true,
  showConfidence: true,
  autoCheckHigh: true
})

const shortcuts = reactive([
  { key: 'newProject', name: '新建项目', keys: 'Ctrl + N' },
  { key: 'saveModel', name: '保存模型', keys: 'Ctrl + S' },
  { key: 'autoLayout', name: '自动布局', keys: 'Ctrl + L' },
  { key: 'exportDoc', name: '导出文档', keys: 'Ctrl + E' },
  { key: 'openSettings', name: '打开设置', keys: 'Ctrl + ,' }
])

const protocols = ['OpenAI', 'DeepSeek']

const presetUrls = [
  { label: '官网', value: '' },
  { label: '智谱', value: 'https://open.bigmodel.cn/api/paas/v4' },
  { label: 'MiMo', value: 'https://api.mimo.chat/v1' },
  { label: 'DeepSeek', value: 'https://api.deepseek.com/v1' },
  { label: '豆包', value: 'https://ark.cn-beijing.volces.com/api/v3' },
  { label: '百度', value: 'https://qianfan.chatbaidu.com/v1' },
  { label: '讯飞', value: 'https://xinghuo.xfyun.cn/v1' }
]

const showKeyMap = reactive({})

const providers = reactive([])

const mapApiToProvider = (raw) => ({
  id: raw.id,
  name: raw.name || raw.provider_name || '',
  enabled: raw.enabled ?? raw.is_active ?? true,
  protocol: raw.protocol || (raw.api_type === 'deepseek' ? 'DeepSeek' : 'OpenAI'),
  endpoint_path: raw.endpoint_path || '/chat/completions',
  base_url: raw.base_url || raw.api_base || '',
  api_key: raw.api_key || raw.api_secret || '',
  timeout: raw.timeout ?? raw.timeout_seconds ?? 60,
  rateUnlimited: raw.rateUnlimited ?? (raw.rate_limit === 0),
  rateLimit: raw.rateLimit ?? raw.rate_limit ?? 50,
  models: Array.isArray(raw.models) ? raw.models : (raw.model ? [raw.model] : []),
  newModel: '',
  _isNew: false,
  _saving: false,
  _testing: false,
  _testResult: raw._testResult || null
})

const mapProviderToApi = (provider) => ({
  name: provider.name,
  provider: provider.protocol === 'DeepSeek' ? 'deepseek' : 'openai',
  protocol: provider.protocol,
  api_type: provider.protocol === 'DeepSeek' ? 'deepseek' : 'openai',
  base_url: provider.base_url,
  endpoint_path: provider.endpoint_path,
  api_key: provider.api_key,
  timeout_seconds: provider.timeout,
  rate_limit: provider.rateUnlimited ? 0 : provider.rateLimit,
  models: provider.models,
  enabled: provider.enabled,
  is_active: provider.enabled
})

const loadConfigs = async () => {
  loadingConfigs.value = true
  try {
    const data = await getLLMConfigs()
    const list = Array.isArray(data) ? data : (data?.items || data?.configs || [])
    providers.splice(0, providers.length, ...list.map(mapApiToProvider))
    if (providers.length && activeProviderId.value === null) {
      activeProviderId.value = providers[0].id
    }
  } catch (e) {
    ElMessage.error(t('llm.messages.loadFailed'))
  } finally {
    loadingConfigs.value = false
  }
}

const toggleExpand = (id) => {
  expandedId.value = expandedId.value === id ? null : id
}

const selectProvider = (provider) => {
  activeProviderId.value = provider.id
}

const toggleKeyVisibility = (id) => {
  showKeyMap[id] = !showKeyMap[id]
}

const addProvider = () => {
  const tempId = `temp-${Date.now()}`
  const p = {
    id: tempId, name: '', enabled: true, protocol: 'OpenAI',
    endpoint_path: '/chat/completions', base_url: '',
    api_key: '', timeout: 60,
    rateUnlimited: false, rateLimit: 50, models: [],
    newModel: '',
    _isNew: true,
    _saving: false,
    _testing: false,
    _testResult: null
  }
  providers.push(p)
  expandedId.value = tempId
  activeProviderId.value = tempId
}

const deleteProvider = async (provider) => {
  if (typeof provider.id === 'number' && !provider._isNew) {
    try {
      await ElMessageBox.confirm(
        t('llm.messages.confirmDelete'),
        t('llm.messages.deleteTitle'),
        { type: 'warning', confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel') }
      )
    } catch {
      return
    }
    try {
      await deleteLLMConfig(provider.id)
      ElMessage.success(t('llm.messages.configDeleted'))
    } catch (e) {
      ElMessage.warning(t('llm.messages.deleteFailed'))
    }
  }
  const idx = providers.findIndex(p => p.id === provider.id)
  if (idx > -1) providers.splice(idx, 1)
  if (expandedId.value === provider.id) expandedId.value = null
  if (activeProviderId.value === provider.id) activeProviderId.value = providers[0]?.id || null
}

const saveProvider = async (provider) => {
  if (!provider.name || !provider.base_url || !provider.api_key) {
    ElMessage.warning(t('llm.messages.needFields'))
    return
  }
  provider._saving = true
  try {
    const payload = mapProviderToApi(provider)
    if (provider._isNew || typeof provider.id !== 'number') {
      const data = await saveLLMConfig(payload)
      if (data?.id) provider.id = data.id
      provider._isNew = false
      ElMessage.success(t('llm.messages.configCreated'))
    } else {
      await updateLLMConfig(provider.id, payload)
      ElMessage.success(t('llm.messages.configSaved'))
    }
  } catch (e) {
    ElMessage.error(t('llm.messages.saveFailed'))
  } finally {
    provider._saving = false
  }
}

const testProvider = async (provider) => {
  if (!provider.base_url || !provider.api_key) {
    ElMessage.warning(t('llm.messages.needKey'))
    return
  }
  provider._testing = true
  provider._testResult = null
  try {
    const payload = mapProviderToApi(provider)
    const data = await testLLMConfig(payload)
    provider._testResult = { ok: data?.ok ?? data?.success ?? true, msg: data?.message || '' }
    if (provider._testResult.ok) {
      ElMessage.success(t('llm.messages.testSuccess'))
    } else {
      ElMessage.error(provider._testResult.msg || t('llm.messages.testFailed'))
    }
  } catch (e) {
    provider._testResult = { ok: false, msg: e?.message || t('llm.messages.testFailed') }
    ElMessage.error(t('llm.messages.testFailed'))
  } finally {
    provider._testing = false
  }
}

const addModel = (provider) => {
  if (provider.newModel && !provider.models.includes(provider.newModel)) {
    provider.models.push(provider.newModel)
    provider.newModel = ''
  }
}

const removeModel = (provider, idx) => {
  provider.models.splice(idx, 1)
}

const importFromCurl = (provider) => {
  if (!curlText.value.trim()) return
  const match = curlText.value.match(/-H\s*['"]Authorization:\s*Bearer\s+([^'"]+)['"]/)
  if (match) provider.api_key = match[1]
  const urlMatch = curlText.value.match(/curl\s+['"]([^'"]+)['"]/)
  if (urlMatch) {
    const fullUrl = urlMatch[1]
    const pathMatch = fullUrl.match(/^(https?:\/\/[^/]+)(\/[^?]*)?/)
    if (pathMatch) {
      provider.base_url = pathMatch[1]
      const path = pathMatch[2] || '/'
      if (path.includes('/chat/completions')) provider.endpoint_path = '/chat/completions'
      else if (path.includes('/responses')) provider.endpoint_path = '/responses'
    }
  }
  curlText.value = ''
}

onMounted(() => {
  loadConfigs()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.settings-root {
  display: flex;
  flex-direction: column;
  height: 560px;
  background: $bg-white;
  overflow: hidden;
}

.settings-header {
  height: 52px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  border-bottom: 1px solid $border-light;
  flex-shrink: 0;
}

.settings-title {
  font-size: 15px;
  font-weight: 700;
  color: $text-primary;
}

.settings-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.settings-nav {
  width: 150px;
  background: $bg-light;
  border-right: 1px solid $border-light;
  padding: 16px 10px;
  flex-shrink: 0;
  overflow: auto;
  height: 100%;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: $radius-md;
  font-size: 13px;
  font-weight: 500;
  color: $text-regular;
  cursor: pointer;
  transition: $transition-base;
  margin-bottom: 4px;

  &:hover {
    background: rgba(59, 130, 246, 0.06);
    color: $text-primary;
  }

  &.active {
    background: rgba(59, 130, 246, 0.1);
    color: $primary-color;
    font-weight: 600;

    .el-icon {
      color: $primary-color;
    }
  }
}

.settings-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.content-header {
  padding: 20px 28px 12px;
  border-bottom: 1px solid $border-light;
  flex-shrink: 0;

  h3 {
    font-size: 17px;
    font-weight: 700;
    color: $text-primary;
    margin: 0;
  }

  p {
    font-size: 12px;
    color: $text-secondary;
    margin: 4px 0 0;
  }
}

.config-section {
  flex: 1;
  padding: 8px 28px 20px;
  overflow: auto;
}

.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid $border-light;

  &:last-child {
    border-bottom: none;
  }

  .config-info {
    flex: 1;
  }

  .config-label {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
  }

  .config-desc {
    font-size: 11px;
    color: $text-secondary;
    margin-top: 3px;
  }
}

.models-wrapper {
  flex: 1;
  padding: 20px 28px;
  overflow-y: auto;
  min-height: 0;
}

.provider-list {
  .cards {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
}

.provider-card {
  border: 1px solid $border-light;
  border-radius: 12px;
  background: $bg-white;
  overflow: hidden;
  transition: $transition-base;

  &:hover {
    border-color: rgba(59, 130, 246, 0.3);
  }

  &.expanded {
    border-color: $primary-color;
    box-shadow: 0 2px 12px rgba(59, 130, 246, 0.1);
  }
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: rgba(248, 250, 252, 0.6);
  }
}

.card-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.drag-handle {
  color: $text-placeholder;
  font-size: 16px;
  letter-spacing: -2px;
  user-select: none;
  cursor: grab;
  font-weight: 700;
}

.provider-name {
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
}

.card-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mini-switch {
  :deep(.el-switch__core) {
    height: 20px;
    min-width: 36px;
    border-radius: 10px;
  }
  :deep(.el-switch__action) {
    width: 16px;
    height: 16px;
  }
}

.action-icon {
  color: $text-secondary;
  cursor: pointer;
  transition: $transition-base;
  padding: 4px;

  &:hover {
    color: $text-primary;
  }

  &.delete:hover {
    color: #EF4444;
  }

  &.expand-arrow {
    transition: transform 0.2s;

    &.rotated {
      transform: rotate(180deg);
    }
  }
}

.card-body {
  border-top: 1px solid $border-light;
  padding: 20px 16px;
  background: $bg-light;
}

.body-section {
  margin-bottom: 18px;

  &:last-child {
    margin-bottom: 0;
  }

  &.inline-fields {
    .inline-field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
  }
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
  margin-bottom: 8px;
}

.curl-collapse,
.ref-collapse {
  background: $bg-white;
  border: 1px solid $border-light;
  border-radius: 8px;

  :deep(.el-collapse-item__header) {
    padding: 0 14px;
    height: 44px;
    border-bottom: none;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
  }

  :deep(.el-collapse-item__content) {
    padding: 0 14px 14px;
  }

  :deep(.el-collapse-item__wrap) {
    border-bottom: none;
  }
}

.curl-title,
.ref-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.curl-import {
  display: flex;
  flex-direction: column;
  gap: 10px;

  .el-textarea {
    :deep(textarea) {
      font-family: 'SF Mono', Consolas, monospace;
      font-size: 12px;
    }
  }
}

.protocol-tabs {
  display: flex;
  gap: 0;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid $border-light;
  width: fit-content;
}

.protocol-tab {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  color: $text-regular;
  cursor: pointer;
  transition: $transition-base;
  background: $bg-white;

  &:hover {
    background: $bg-light;
  }

  &.active {
    background: $primary-color;
    color: white;
  }
}

.ref-config {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ref-endpoint {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;

  .ref-label {
    font-size: 13px;
    font-weight: 500;
    color: $text-primary;
  }
}

.ref-url {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .ref-label {
    font-size: 12px;
    color: $text-secondary;
    line-height: 1.5;
  }
}

.preset-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
}

.preset-tag {
  padding: 4px 12px;
  border-radius: 16px;
  background: $bg-white;
  border: 1px solid $border-light;
  font-size: 12px;
  color: $text-regular;
  cursor: pointer;
  transition: $transition-base;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
  }

  &.active {
    background: rgba(59, 130, 246, 0.1);
    border-color: $primary-color;
    color: $primary-color;
  }
}

.key-input-wrap {
  position: relative;

  .key-toggle {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: $text-placeholder;
    cursor: pointer;
    z-index: 1;

    &:hover {
      color: $text-regular;
    }
  }

  .el-input {
    input {
      padding-right: 36px;
    }
  }
}

.timeout-input {
  display: flex;
  align-items: center;
  gap: 10px;

  .unit {
    font-size: 13px;
    color: $text-secondary;
  }
}

.rate-limit-row {
  display: flex;
  align-items: center;
  gap: 14px;

  .rate-slider {
    flex: 1;
    max-width: 300px;
    margin: 0;
  }

  .rate-value {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
    min-width: 30px;
    text-align: right;
  }

  .rate-unit {
    font-size: 13px;
    color: $text-secondary;
  }

  .rate-value-unlimited {
    font-size: 13px;
    font-weight: 600;
    color: $text-secondary;
  }
}

.rate-label {
  margin-top: 8px !important;
  font-size: 12px !important;
  color: $text-secondary !important;
  font-weight: 400 !important;
}

.provider-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid $border-light;
}

.model-input-row {
  display: flex;
  gap: 10px;
}

.model-tags {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  .model-tag {
    border-radius: 6px;
    background: rgba(59, 130, 246, 0.08);
    color: $primary-color;
    border: none;
  }
}

.add-provider-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  margin-top: 4px;
  border: 2px dashed $border-color;
  border-radius: 12px;
  color: $text-secondary;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: $transition-base;
  background: transparent;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
    background: rgba(59, 130, 246, 0.03);
  }
}

.settings-footer {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 24px;
  border-top: 1px solid $border-light;
  flex-shrink: 0;
  background: $bg-white;
}

.shortcut-list {
  padding: 16px 28px;
}

.shortcut-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid $border-light;

  .s-name {
    font-size: 13px;
    color: $text-regular;
    font-weight: 500;
  }
}

.about-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 28px;
  text-align: center;

  .about-logo {
    width: 72px;
    height: 72px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.1));
    border-radius: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
  }

  .about-name {
    font-size: 18px;
    font-weight: 700;
    color: $text-primary;
  }

  .about-version {
    font-size: 12px;
    color: $text-secondary;
    margin-top: 4px;
  }

  .about-desc {
    font-size: 13px;
    color: $text-regular;
    line-height: 1.7;
    margin-top: 20px;
    max-width: 420px;
    white-space: pre-line;
  }

  .about-links {
    display: flex;
    gap: 12px;
    margin-top: 24px;
  }
}

html.dark .settings-root {
  background: #252526;

  :deep(.settings-header) {
    background: #252526;
    border-bottom-color: #3c3c3c;
  }
  :deep(.settings-title) { color: #f8fafc; }

  :deep(.settings-nav) {
    background: #252526;
    border-right-color: #3c3c3c;
  }
  :deep(.nav-item) {
    color: #94a3b8;
    &:hover { background: rgba(59, 130, 246, 0.1); color: #e2e8f0; }
    &.active { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
  }

  :deep(.content-header) {
    border-bottom-color: #3c3c3c;
    h3 { color: #f8fafc; }
    p { color: #94a3b8; }
  }

  :deep(.config-row) { border-bottom-color: #3c3c3c; }
  :deep(.config-label) { color: #f8fafc; }
  :deep(.config-desc) { color: #94a3b8; }
  :deep(.shortcut-row) { border-bottom-color: #3c3c3c; }
  :deep(.s-name) { color: #e2e8f0; }
  :deep(.settings-footer) {
    background: #252526;
    border-top-color: #3c3c3c;
  }

  :deep(.about-section) {
    .about-name { color: #f8fafc; }
    .about-version { color: #94a3b8; }
    .about-desc { color: #cbd5e1; }
  }

  :deep(.provider-card) {
    background: #252526;
    border-color: #3c3c3c;
    &.expanded {
      border-color: #3b82f6;
      box-shadow: 0 2px 12px rgba(59, 130, 246, 0.15);
    }
  }
  :deep(.card-header) {
    &:hover { background: rgba(255, 255, 255, 0.03); }
  }
  :deep(.provider-name) { color: #f8fafc; }
  :deep(.card-body) {
    background: #252526;
    border-top-color: #3c3c3c;
  }
  :deep(.field-label) { color: #e2e8f0; }
  :deep(.add-provider-btn) {
    border-color: #3c3c3c;
    color: #94a3b8;
    &:hover { border-color: #3b82f6; color: #60a5fa; background: rgba(59, 130, 246, 0.05); }
  }
}
</style>
