<template>
  <div class="settings-root">
    <div class="settings-header">
      <el-icon :size="22" color="#3B82F6"><Setting /></el-icon>
      <span class="settings-title">设置</span>
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
          <span>{{ item.label }}</span>
        </div>
      </aside>

      <div class="settings-content">
        <template v-if="activeNav === 'general'">
          <div class="content-header">
            <h3>通用配置</h3>
            <p>调整应用基础设置</p>
          </div>
          <div class="config-section">
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">主题模式</div>
                <div class="config-desc">选择应用的外观主题</div>
              </div>
              <el-radio-group v-model="general.theme">
                <el-radio-button value="light">浅色</el-radio-button>
                <el-radio-button value="dark">深色</el-radio-button>
                <el-radio-button value="auto">跟随系统</el-radio-button>
              </el-radio-group>
            </div>
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">语言</div>
                <div class="config-desc">界面显示语言</div>
              </div>
              <el-select v-model="general.language" style="width: 160px;">
                <el-option label="简体中文" value="zh-CN" />
                <el-option label="English" value="en-US" />
              </el-select>
            </div>
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">自动保存分析结果</div>
                <div class="config-desc">分析完成后自动保存到本地</div>
              </div>
              <el-switch v-model="general.autoSave" />
            </div>
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">显示 AI 推断置信度</div>
                <div class="config-desc">在建议列表中显示模型置信度百分比</div>
              </div>
              <el-switch v-model="general.showConfidence" />
            </div>
            <div class="config-row">
              <div class="config-info">
                <div class="config-label">高置信度默认勾选</div>
                <div class="config-desc">置信度 >= 85% 的建议默认标记为已确认</div>
              </div>
              <el-switch v-model="general.autoCheckHigh" />
            </div>
          </div>
        </template>

        <template v-if="activeNav === 'models'">
          <div class="content-header">
            <h3>模型配置</h3>
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
                      <span class="provider-name">{{ provider.name || '未命名供应商' }}</span>
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
                      <div class="field-label">供应商名称</div>
                      <el-input v-model="provider.name" placeholder="请输入供应商名称" />
                    </div>

                    <div class="body-section">
                      <el-collapse v-model="activeCollapse" class="curl-collapse">
                        <el-collapse-item name="curl">
                          <template #title>
                            <span class="curl-title">
                              <el-icon><Promotion /></el-icon>
                              Curl 导入
                            </span>
                          </template>
                          <div class="curl-import">
                            <el-input
                              v-model="curlText"
                              type="textarea"
                              :rows="4"
                              placeholder="粘贴 curl 命令，自动解析配置..."
                            />
                            <el-button type="primary" size="small" @click="importFromCurl(provider)">导入</el-button>
                          </div>
                        </el-collapse-item>
                      </el-collapse>
                    </div>

                    <div class="body-section">
                      <div class="field-label">API 协议</div>
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
                              参考配置（{{ provider.protocol }} 案例）
                            </span>
                          </template>
                          <div class="ref-config">
                            <div class="ref-endpoint">
                              <span class="ref-label">端点路径：</span>
                              <el-radio-group v-model="provider.endpoint_path" size="small">
                                <el-radio-button value="/chat/completions">/chat/completions</el-radio-button>
                                <el-radio-button value="/responses">/responses</el-radio-button>
                              </el-radio-group>
                            </div>
                            <div class="ref-url">
                              <div class="ref-label">Base URL（不含端点路径，结尾一般 v1/v4 等。完整路径，即是 curl 请求地址。）</div>
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
                      <div class="field-label">密钥</div>
                      <div class="key-input-wrap">
                        <el-input
                          v-model="provider.api_key"
                          :type="showKeyMap[provider.id] ? 'text' : 'password'"
                          placeholder="sk-..."
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
                        <div class="field-label">超时时间（秒）</div>
                        <div class="timeout-input">
                          <el-input-number
                            v-model="provider.timeout"
                            :min="1"
                            :max="600"
                            controls-position="right"
                          />
                          <span class="unit">秒</span>
                        </div>
                      </div>
                    </div>

                    <div class="body-section">
                      <div class="rate-limit-row">
                        <div class="rate-limit-left">
                          <el-checkbox v-model="provider.rateUnlimited">不限制</el-checkbox>
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
                      <div class="field-label rate-label">请求频率限制（0=不限制，1-200）</div>
                    </div>

                    <div class="body-section">
                      <div class="field-label">模型</div>
                      <div class="model-input-row">
                        <el-input
                          v-model="provider.newModel"
                          placeholder="e.g., gpt-4"
                          @keyup.enter="addModel(provider)"
                        />
                        <el-button
                          type="primary"
                          :icon="Plus"
                          @click="addModel(provider)"
                        >添加模型</el-button>
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
                      >测试连接</el-button>
                      <el-button
                        type="primary"
                        :icon="Check"
                        :loading="provider._saving"
                        @click="saveProvider(provider)"
                      >{{ provider.id && !provider._isNew ? '保存配置' : '创建配置' }}</el-button>
                      <el-tag
                        v-if="provider._testResult"
                        :type="provider._testResult.ok ? 'success' : 'danger'"
                        size="small"
                        effect="light"
                      >
                        {{ provider._testResult.ok ? '连接成功' : '连接失败' }}
                      </el-tag>
                    </div>
                  </div>
                </div>
              </transition-group>

              <div class="add-provider-btn" @click="addProvider">
                <el-icon :size="18"><Plus /></el-icon>
                <span>添加新供应商</span>
              </div>
            </div>
          </div>
        </template>

        <template v-if="activeNav === 'shortcuts'">
          <div class="content-header">
            <h3>快捷键</h3>
            <p>自定义操作快捷键</p>
          </div>
          <div class="shortcut-list">
            <div v-for="s in shortcuts" :key="s.name" class="shortcut-row">
              <span class="s-name">{{ s.name }}</span>
              <el-input v-model="s.keys" size="small" style="width: 200px;" />
            </div>
          </div>
        </template>

        <template v-if="activeNav === 'about'">
          <div class="content-header">
            <h3>关于</h3>
          </div>
          <div class="about-section">
            <div class="about-logo">
              <el-icon :size="40" color="#3B82F6"><DataBase /></el-icon>
            </div>
            <div class="about-name">AI Database Architect</div>
            <div class="about-version">版本 v0.1.0</div>
            <div class="about-desc">
              智能数据库 Schema 分析、逻辑外键推断与 ER 模型生成平台。<br/>
              通过 Schema 自动解析、规则候选生成、AI 语义判断、可视化 ER 编辑和文档导出，帮助开发人员快速建立可靠的数据库结构认知。
            </div>
            <div class="about-links">
              <el-button text type="primary" size="small"><el-icon><Link /></el-icon> 文档</el-button>
              <el-button text type="primary" size="small"><el-icon><ChatDotRound /></el-icon> 反馈</el-button>
              <el-button text type="primary" size="small"><el-icon><InfoFilled /></el-icon> 更新日志</el-button>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div class="settings-footer">
      <el-button @click="$emit('close')">关闭</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLLMConfigs, saveLLMConfig, deleteLLMConfig, testLLMConfig, updateLLMConfig } from '@/api/llm'

defineEmits(['close'])

const activeNav = ref('models')
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
  theme: 'light',
  language: 'zh-CN',
  autoSave: true,
  showConfidence: true,
  autoCheckHigh: true
})

const shortcuts = reactive([
  { name: '新建项目', keys: 'Ctrl + N' },
  { name: '保存模型', keys: 'Ctrl + S' },
  { name: '自动布局', keys: 'Ctrl + L' },
  { name: '导出文档', keys: 'Ctrl + E' },
  { name: '打开设置', keys: 'Ctrl + ,' }
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
    ElMessage.error('加载模型配置失败')
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
      await ElMessageBox.confirm('确定删除该模型配置？', '删除确认', { type: 'warning' })
    } catch {
      return
    }
    try {
      await deleteLLMConfig(provider.id)
      ElMessage.success('配置已删除')
    } catch (e) {
      ElMessage.warning('服务端删除失败，已从列表移除')
    }
  }
  const idx = providers.findIndex(p => p.id === provider.id)
  if (idx > -1) providers.splice(idx, 1)
  if (expandedId.value === provider.id) expandedId.value = null
  if (activeProviderId.value === provider.id) activeProviderId.value = providers[0]?.id || null
}

const saveProvider = async (provider) => {
  if (!provider.name || !provider.base_url || !provider.api_key) {
    ElMessage.warning('请填写供应商名称、Base URL 和密钥')
    return
  }
  provider._saving = true
  try {
    const payload = mapProviderToApi(provider)
    if (provider._isNew || typeof provider.id !== 'number') {
      const data = await saveLLMConfig(payload)
      if (data?.id) provider.id = data.id
      provider._isNew = false
      ElMessage.success('配置已创建')
    } else {
      await updateLLMConfig(provider.id, payload)
      ElMessage.success('配置已保存')
    }
  } catch (e) {
    ElMessage.error('保存失败，请检查后端服务')
  } finally {
    provider._saving = false
  }
}

const testProvider = async (provider) => {
  if (!provider.base_url || !provider.api_key) {
    ElMessage.warning('请先填写 Base URL 和密钥')
    return
  }
  provider._testing = true
  provider._testResult = null
  try {
    const payload = mapProviderToApi(provider)
    const data = await testLLMConfig(payload)
    provider._testResult = { ok: data?.ok ?? data?.success ?? true, msg: data?.message || '' }
    if (provider._testResult.ok) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error(provider._testResult.msg || '连接测试失败')
    }
  } catch (e) {
    provider._testResult = { ok: false, msg: e?.message || '连接失败' }
    ElMessage.error('连接测试失败')
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
  }

  .about-links {
    display: flex;
    gap: 12px;
    margin-top: 24px;
  }
}
</style>
