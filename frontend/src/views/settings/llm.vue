<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <div class="page-title">大模型配置中心</div>
        <div class="page-subtitle">配置您的 AI 服务提供商，用于关系分析与文档生成</div>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreate">
        新增配置
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col :span="9">
        <div class="card config-list-card">
          <div class="card-head">
            <div style="font-size: 16px; font-weight: 600;">已保存的模型配置</div>
          </div>

          <div class="config-list">
            <div
              v-for="c in configs"
              :key="c.id"
              class="config-item"
              :class="{ active: selectedId === c.id }"
              @click="selectConfig(c)"
            >
              <div class="provider-logo" :class="c.provider">
                <el-icon v-if="c.provider === 'deepseek'" :size="20"><Cpu /></el-icon>
                <el-icon v-else-if="c.provider === 'gemini'" :size="20"><Promotion /></el-icon>
                <el-icon v-else-if="c.provider === 'qwen'" :size="20"><Odometer /></el-icon>
                <el-icon v-else :size="20"><Setting /></el-icon>
              </div>
              <div class="config-info">
                <div class="config-name">
                  {{ c.name }}
                  <el-tag v-if="c.is_default" size="small" type="warning" effect="light" style="margin-left: 6px;">
                    默认
                  </el-tag>
                </div>
                <div class="config-meta">
                  <span class="provider-name">{{ providerLabelMap[c.provider] }}</span>
                  <span class="dot">·</span>
                  <span>{{ c.model }}</span>
                </div>
                <div class="config-usage">
                  <el-tag size="small" effect="plain" v-for="u in c.usage_list" :key="u" style="margin-right: 4px;">
                    {{ usageLabelMap[u] }}
                  </el-tag>
                </div>
              </div>
              <div class="status-col">
                <el-tooltip :content="c.status_ok ? '连接测试通过' : '连接异常'" placement="left">
                  <el-badge :is-dot="true" :type="c.status_ok ? 'success' : 'danger'" />
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="15">
        <div class="card" v-if="selectedConfig">
          <div class="card-head flex-between">
            <div>
              <div style="font-size: 16px; font-weight: 600;">
                {{ editing ? (form.id ? '编辑配置' : '新增配置') : '配置详情' }}
              </div>
              <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">
                {{ editing ? '修改后请点击保存并测试连接' : '点击编辑按钮可修改配置' }}
              </div>
            </div>
            <div>
              <template v-if="!editing">
                <el-button :icon="Edit" text type="primary" @click="startEdit">编辑</el-button>
                <el-popconfirm title="确定删除该配置？" @confirm="delConfig">
                  <template #reference>
                    <el-button :icon="Delete" text type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </div>
          </div>

          <el-form :model="form" :disabled="!editing" label-width="130px" class="llm-form">
            <el-form-item label="配置名称" required>
              <el-input v-model="form.name" placeholder="例如：默认关系分析模型" />
            </el-form-item>

            <el-form-item label="模型服务商" required>
              <el-select v-model="form.provider" style="width: 100%;" @change="onProviderChange">
                <el-option v-for="p in providers" :key="p.value" :label="p.label" :value="p.value">
                  <div class="provider-option">
                    <span class="po-logo" :class="p.value">
                      <el-icon v-if="p.value === 'deepseek'"><Cpu /></el-icon>
                      <el-icon v-else-if="p.value === 'gemini'"><Promotion /></el-icon>
                      <el-icon v-else-if="p.value === 'qwen'"><Odometer /></el-icon>
                      <el-icon v-else><Setting /></el-icon>
                    </span>
                    <div class="po-text">
                      <div class="po-name">{{ p.label }}</div>
                      <div class="po-desc">{{ p.desc }}</div>
                    </div>
                    <el-tag v-if="p.recommended" size="small" type="success" effect="light">推荐</el-tag>
                  </div>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="API Base URL" required>
              <el-input v-model="form.base_url" placeholder="https://api.example.com/v1" />
            </el-form-item>

            <el-form-item label="API Key" required>
              <div style="display: flex; gap: 8px; width: 100%;">
                <el-input
                  v-model="form.api_key"
                  :type="showKey ? 'text' : 'password'"
                  placeholder="sk-..."
                  style="flex: 1;"
                />
                <el-button @click="showKey = !showKey">
                  <el-icon :size="16">
                    <component :is="showKey ? 'Hide' : 'View'" />
                  </el-icon>
                </el-button>
              </div>
              <div class="form-tip">
                <el-icon :size="12" color="#94A3B8"><Lock /></el-icon>
                密钥将使用 AES-256 加密存储，前端不以明文回传
              </div>
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="模型名称" required>
                  <el-select v-model="form.model" filterable allow-create style="width: 100%;">
                    <el-option v-for="m in modelOptions" :key="m" :label="m" :value="m" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Temperature">
                  <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" :marks="{0:'0',1:'1',2:'2'}" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :span="8">
                <el-form-item label="最大 Token">
                  <el-input-number v-model="form.max_tokens" :min="256" :max="128000" :step="256" style="width: 100%;" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="请求超时(秒)">
                  <el-input-number v-model="form.timeout_seconds" :min="10" :max="600" :step="10" style="width: 100%;" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="最大重试">
                  <el-input-number v-model="form.max_retries" :min="0" :max="10" style="width: 100%;" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-divider content-position="left" style="margin: 8px 0 16px;">
              <span style="font-size: 13px; color: #64748B; font-weight: 500;">用途设置</span>
            </el-divider>

            <el-form-item label="配置用途">
              <el-checkbox-group v-model="form.usage_list">
                <el-checkbox value="relation_analysis" border>关系分析</el-checkbox>
                <el-checkbox value="doc_generation" border>文档生成</el-checkbox>
                <el-checkbox value="qa" border>通用问答</el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <el-form-item label="设为默认">
              <el-switch v-model="form.is_default" />
              <span style="margin-left: 8px; font-size: 12px; color: #94A3B8;">
                当没有指定模型时，优先使用此配置（每个用途仅一个默认）
              </span>
            </el-form-item>

            <el-divider v-if="!editing && testResult" style="margin: 4px 0 12px;" />

            <div v-if="!editing && testResult" class="test-panel" :class="testResult.ok ? 'ok' : 'fail'">
              <div class="test-head">
                <el-icon v-if="testResult.ok" color="#10B981" :size="18"><CircleCheckFilled /></el-icon>
                <el-icon v-else color="#EF4444" :size="18"><CircleCloseFilled /></el-icon>
                <span class="test-title">{{ testResult.ok ? '最近一次连接测试成功' : '最近一次连接测试失败' }}</span>
                <span class="test-time">{{ testResult.time }}</span>
                <span class="test-cost">耗时 {{ testResult.cost }}ms</span>
              </div>
              <div class="test-detail" v-if="!testResult.ok">{{ testResult.msg }}</div>
            </div>

            <div class="form-actions-row" v-if="editing">
              <el-button @click="cancelEdit">取消</el-button>
              <div>
                <el-button :icon="Connection" :loading="testing" @click="testConnectionForm">
                  测试连接
                </el-button>
                <el-button type="primary" :icon="Check" @click="saveForm">保存配置</el-button>
              </div>
            </div>
          </el-form>
        </div>

        <el-empty v-else description="请选择左侧配置进行查看" class="empty-detail" />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'

const showKey = ref(false)
const testing = ref(false)
const editing = ref(false)
const selectedId = ref(1)
const testResult = ref(null)

const providerLabelMap = {
  deepseek: 'DeepSeek',
  gemini: 'Google Gemini',
  qwen: '通义千问',
  openai: 'OpenAI 兼容'
}
const usageLabelMap = {
  relation_analysis: '关系分析',
  doc_generation: '文档生成',
  qa: '通用问答'
}

const providers = [
  { value: 'deepseek', label: 'DeepSeek', desc: '国产模型，推理性能优秀', recommended: true },
  { value: 'gemini', label: 'Google Gemini', desc: '多模态理解能力强', recommended: false },
  { value: 'qwen', label: '阿里云通义千问', desc: '中文语义理解优势', recommended: true },
  { value: 'openai', label: 'OpenAI Compatible', desc: '兼容 OpenAI 协议的自定义服务', recommended: false }
]

const configs = reactive([
  {
    id: 1, name: '默认关系分析模型', provider: 'deepseek', model: 'deepseek-chat',
    base_url: 'https://api.deepseek.com', api_key: 'sk-********C2kQ',
    temperature: 0.2, max_tokens: 4096, timeout_seconds: 60, max_retries: 2,
    usage_list: ['relation_analysis'], is_default: true, status_ok: true
  },
  {
    id: 2, name: '文档生成模型', provider: 'qwen', model: 'qwen-max',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', api_key: 'sk-********4aF9',
    temperature: 0.6, max_tokens: 8192, timeout_seconds: 90, max_retries: 2,
    usage_list: ['doc_generation'], is_default: true, status_ok: true
  },
  {
    id: 3, name: 'Gemini 多模态测试', provider: 'gemini', model: 'gemini-pro',
    base_url: 'https://generativelanguage.googleapis.com/v1beta', api_key: 'AIza************xY',
    temperature: 0.4, max_tokens: 4096, timeout_seconds: 45, max_retries: 1,
    usage_list: ['qa'], is_default: false, status_ok: false
  }
])

const form = reactive({
  id: null, name: '', provider: 'deepseek', base_url: 'https://api.deepseek.com',
  api_key: '', model: 'deepseek-chat', temperature: 0.2, max_tokens: 4096,
  timeout_seconds: 60, max_retries: 2, usage_list: ['relation_analysis'], is_default: false
})

const selectedConfig = computed(() => configs.find(c => c.id === selectedId.value))

const modelOptions = computed(() => {
  const map = {
    deepseek: ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner'],
    gemini: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro'],
    qwen: ['qwen-max', 'qwen-plus', 'qwen-turbo', 'qwen-long'],
    openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo']
  }
  return map[form.provider] || []
})

const selectConfig = (c) => {
  selectedId.value = c.id
  editing.value = false
  testResult.value = {
    ok: c.status_ok, time: '2026-08-08 14:32:10', cost: c.status_ok ? 245 : 5000,
    msg: c.status_ok ? '' : '连接超时：API 端点不可达（443端口），请检查网络或 Base URL 设置'
  }
  Object.assign(form, JSON.parse(JSON.stringify(c)))
}

const openCreate = () => {
  editing.value = true
  selectedId.value = null
  testResult.value = null
  Object.assign(form, {
    id: null, name: '', provider: 'deepseek', base_url: 'https://api.deepseek.com',
    api_key: '', model: 'deepseek-chat', temperature: 0.2, max_tokens: 4096,
    timeout_seconds: 60, max_retries: 2, usage_list: ['relation_analysis'], is_default: false
  })
}

const startEdit = () => { editing.value = true }
const cancelEdit = () => {
  editing.value = false
  if (selectedConfig.value) Object.assign(form, JSON.parse(JSON.stringify(selectedConfig.value)))
}

const onProviderChange = () => {
  const defaults = {
    deepseek: 'https://api.deepseek.com',
    gemini: 'https://generativelanguage.googleapis.com/v1beta',
    qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    openai: 'https://api.openai.com/v1'
  }
  form.base_url = defaults[form.provider] || ''
  if (modelOptions.value.length) form.model = modelOptions.value[0]
}

const testConnectionForm = async () => {
  testing.value = true
  await new Promise(r => setTimeout(r, 1500))
  testing.value = false
  testResult.value = {
    ok: form.api_key.length > 5,
    time: new Date().toLocaleString('zh-CN'),
    cost: Math.floor(Math.random() * 400 + 100),
    msg: 'API Key 格式无效或认证失败，请检查凭据'
  }
}

const saveForm = () => {
  if (form.id) {
    const idx = configs.findIndex(c => c.id === form.id)
    if (idx > -1) Object.assign(configs[idx], JSON.parse(JSON.stringify(form)))
  } else {
    const id = Math.max(...configs.map(c => c.id)) + 1
    const n = { ...JSON.parse(JSON.stringify(form)), id, status_ok: false }
    configs.push(n)
    selectedId.value = id
  }
  editing.value = false
}

const delConfig = () => {
  const idx = configs.findIndex(c => c.id === selectedId.value)
  if (idx > -1) configs.splice(idx, 1)
  selectedId.value = configs[0]?.id || null
}

// init
selectConfig(configs[0])
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.config-list-card {
  padding: 20px 16px;
}

.card-head {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid $border-light;
}

.config-list {
  .config-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 12px;
    border-radius: $radius-md;
    cursor: pointer;
    transition: $transition-base;
    margin-bottom: 6px;
    border: 1px solid transparent;

    &:hover { background: $bg-light; }
    &.active {
      background: rgba(59, 130, 246, 0.06);
      border-color: rgba(59, 130, 246, 0.2);
    }
  }
}

.provider-logo {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: white;

  &.deepseek { background: linear-gradient(135deg, #4285F4, #34A853); }
  &.gemini { background: linear-gradient(135deg, #8E75B2, #4285F4); }
  &.qwen { background: linear-gradient(135deg, #6A5AF9, #FF6A88); }
  &.openai { background: linear-gradient(135deg, #10A37F, #1A7F64); }
}

.config-info {
  flex: 1;
  min-width: 0;
}

.config-name {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.config-meta {
  font-size: 11px;
  color: $text-secondary;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 5px;

  .provider-name { font-weight: 500; color: $text-regular; }
  .dot { color: #CBD5E1; }
}

.config-usage { margin-top: 6px; }

.status-col {
  padding: 4px;
}

.provider-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

.po-logo {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;

  &.deepseek { background: linear-gradient(135deg, #4285F4, #34A853); }
  &.gemini { background: linear-gradient(135deg, #8E75B2, #4285F4); }
  &.qwen { background: linear-gradient(135deg, #6A5AF9, #FF6A88); }
  &.openai { background: linear-gradient(135deg, #10A37F, #1A7F64); }
}

.po-text {
  flex: 1;
}

.po-name {
  font-size: 13px;
  font-weight: 600;
  color: $text-primary;
}

.po-desc {
  font-size: 11px;
  color: $text-secondary;
  margin-top: 1px;
}

.llm-form {
  :deep(.el-form-item__label) {
    font-weight: 500;
    color: $text-regular;
  }
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: $text-placeholder;
  margin-top: 6px;
}

.test-panel {
  padding: 14px 16px;
  border-radius: $radius-md;
  margin-bottom: 8px;

  &.ok {
    background: rgba(16, 185, 129, 0.06);
    border: 1px solid rgba(16, 185, 129, 0.2);
  }

  &.fail {
    background: rgba(239, 68, 68, 0.04);
    border: 1px solid rgba(239, 68, 68, 0.2);
  }

  .test-head {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .test-title {
    font-size: 13px;
    font-weight: 600;
    color: $text-primary;
  }

  .test-time {
    margin-left: auto;
    font-size: 11px;
    color: $text-secondary;
  }

  .test-cost {
    font-size: 11px;
    color: $text-secondary;
    padding: 2px 8px;
    background: $bg-white;
    border-radius: 4px;
    border: 1px solid $border-light;
    margin-left: 8px;
  }

  .test-detail {
    margin-top: 8px;
    font-size: 12px;
    color: #B91C1C;
    padding: 8px 10px;
    background: rgba(239, 68, 68, 0.06);
    border-radius: 6px;
  }
}

.form-actions-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 20px;
  margin-top: 12px;
  border-top: 1px solid $border-light;
}

.empty-detail {
  padding: 80px 0;
}
</style>
