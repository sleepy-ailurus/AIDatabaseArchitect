<template>
  <div class="table-node-wrap" :class="{ selected: selected }">
    <!-- Top anchor points -->
    <Handle
      type="target"
      :position="Position.Top"
      id="top-target"
      class="table-anchor top-anchor-left"
    />
    <Handle
      type="source"
      :position="Position.Top"
      id="top-source"
      class="table-anchor top-anchor-right"
    />

    <div class="node-header" :style="headerStyle">
      <div class="node-title">
        <el-icon :size="14"><DataBase /></el-icon>
        <span v-if="!editing" @dblclick="startEdit">{{ data.name }}</span>
        <input
          v-else
          ref="nameInputRef"
          v-model="localName"
          class="name-input"
          @blur="commitName"
          @keyup.enter="commitName"
          @keyup.esc="cancelEdit"
        />
      </div>
      <div class="header-actions">
        <span class="field-count" v-if="data.columns">{{ t('erModel.node.fieldCount', { count: data.columns.length }) }}</span>
        <el-dropdown trigger="click" @command="handleMenuCommand">
          <el-button text circle size="small" class="more-btn" @click.stop>
            <el-icon :size="14"><MoreFilled /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="addColumn">
                <el-icon><Plus /></el-icon> {{ t('erModel.node.addField') }}
              </el-dropdown-item>
              <el-dropdown-item command="copy">
                <el-icon><CopyDocument /></el-icon> {{ t('erModel.node.duplicate') }}
              </el-dropdown-item>
              <el-dropdown-item command="delete" divided style="color: #EF4444;">
                <el-icon><Delete /></el-icon> {{ t('erModel.node.delete') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="node-body">
      <div
        v-for="(col, idx) in displayColumns"
        :key="col.name"
        class="column-row"
        :class="{
          pk: col.isPK,
          fk: col.isFK,
          uk: col.isUnique,
          'ai-suggested': col.aiSuggested
        }"
      >
        <span class="col-key">
          <span v-if="col.isPK" class="key-icon pk" :title="t('erModel.node.primaryKey')">🔑</span>
          <span v-else-if="col.isFK" class="key-icon fk" :title="t('erModel.node.foreignKey')">🔗</span>
          <span v-else-if="col.isUnique" class="key-icon uk" :title="t('erModel.node.unique')">🔐</span>
          <span v-else-if="col.aiSuggested" class="key-icon ai" :title="t('erModel.node.aiSuggest')">✨</span>
        </span>
        <span class="col-name">{{ col.name }}</span>
        <span class="col-type" :class="getTypeClass(col.type)">{{ col.type }}</span>
      </div>
      <div v-if="data.columns && data.columns.length > maxDisplay" class="more-fields">
        + {{ t('erModel.node.moreFields', { count: data.columns.length - maxDisplay }) }}
      </div>
      <div class="column-footer" v-if="data.comment">
        {{ data.comment }}
      </div>
    </div>

    <!-- Bottom anchor points -->
    <Handle
      type="target"
      :position="Position.Bottom"
      id="bottom-target"
      class="table-anchor bottom-anchor-left"
    />
    <Handle
      type="source"
      :position="Position.Bottom"
      id="bottom-source"
      class="table-anchor bottom-anchor-right"
    />

    <!-- Left anchor points -->
    <Handle
      type="target"
      :position="Position.Left"
      id="left-target"
      class="table-anchor side-anchor left-target"
    />
    <Handle
      type="source"
      :position="Position.Left"
      id="left-source"
      class="table-anchor side-anchor left-source"
    />

    <!-- Right anchor points -->
    <Handle
      type="target"
      :position="Position.Right"
      id="right-target"
      class="table-anchor side-anchor right-target"
    />
    <Handle
      type="source"
      :position="Position.Right"
      id="right-source"
      class="table-anchor side-anchor right-source"
    />
  </div>
</template>

<script setup>
import { computed, ref, nextTick, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { Handle, Position } from '@vue-flow/core'
import { ElMessageBox, ElMessage } from 'element-plus'

const { t } = useI18n()

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
  id: { type: String, default: '' }
})

const emit = defineEmits(['rename'])

const nodeActions = inject('nodeActions', null)

const maxDisplay = 12

const editing = ref(false)
const localName = ref('')
const nameInputRef = ref(null)

const headerColors = [
  'linear-gradient(135deg, #3B82F6, #60A5FA)',
  'linear-gradient(135deg, #10B981, #34D399)',
  'linear-gradient(135deg, #F59E0B, #FBBF24)',
  'linear-gradient(135deg, #6366F1, #818CF8)',
  'linear-gradient(135deg, #EC4899, #F472B6)',
  'linear-gradient(135deg, #8B5CF6, #A78BFA)'
]

const headerStyle = computed(() => {
  let hash = 0
  const name = props.data.name || ''
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return { background: headerColors[Math.abs(hash) % headerColors.length] }
})

const displayColumns = computed(() => {
  const cols = props.data.columns || []
  return cols.slice(0, maxDisplay)
})

const getTypeClass = (type) => {
  const t = (type || '').toUpperCase()
  if (t.includes('INT') || t.includes('BIT')) return 'type-numeric'
  if (t.includes('DECIMAL') || t.includes('FLOAT') || t.includes('DOUBLE')) return 'type-decimal'
  if (t.includes('CHAR') || t.includes('TEXT') || t.includes('JSON') || t.includes('ENUM')) return 'type-string'
  if (t.includes('DATE') || t.includes('TIME')) return 'type-time'
  if (t.includes('BLOB') || t.includes('BINARY')) return 'type-binary'
  return 'type-default'
}

const startEdit = async () => {
  editing.value = true
  localName.value = props.data.name
  await nextTick()
  nameInputRef.value?.focus()
  nameInputRef.value?.select()
}

const commitName = () => {
  editing.value = false
  if (localName.value && localName.value !== props.data.name) {
    emit('rename', localName.value)
  }
}

const cancelEdit = () => {
  editing.value = false
}

const handleMenuCommand = async (cmd) => {
  const nodeId = props.id
  if (cmd === 'addColumn') {
    nodeActions?.openAddColumn(nodeId)
  } else if (cmd === 'copy') {
    nodeActions?.copyNode(nodeId)
  } else if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm(
        t('erModel.node.deleteConfirmMsg', { name: props.data.name }),
        t('erModel.node.deleteConfirmTitle'),
        { type: 'warning', confirmButtonText: t('erModel.node.deleteConfirmBtn'), cancelButtonText: t('common.cancel') }
      )
      nodeActions?.deleteNode(nodeId)
    } catch {
      // cancelled
    }
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.table-node-wrap {
  width: 240px;
  background: $bg-white;
  border-radius: 10px;
  overflow: visible;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
  border: 2px solid transparent;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  position: relative;

  &:hover {
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.12);

    .table-anchor {
      opacity: 1;
    }
  }

  &.selected {
    border-color: $primary-color;
    box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15), 0 10px 15px -3px rgba(0, 0, 0, 0.08);

    .table-anchor {
      opacity: 1;
    }
  }
}

.node-header {
  padding: 8px 12px;
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  border-radius: 8px 8px 0 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.more-btn {
  color: rgba(255, 255, 255, 0.9) !important;
  background: transparent !important;
  border-color: transparent !important;
  width: 24px !important;
  height: 24px !important;
  padding: 0 !important;

  &:hover,
  &:focus,
  &:active {
    color: #fff !important;
    background: rgba(255, 255, 255, 0.2) !important;
    border-color: transparent !important;
  }

  :deep(.el-icon) {
    color: inherit !important;
  }
}

.node-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  font-family: 'SF Mono', Consolas, monospace;
  min-width: 0;
  flex: 1;

  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.name-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: rgba(255, 255, 255, 0.25);
  color: white;
  font-size: 13px;
  font-weight: 700;
  font-family: 'SF Mono', Consolas, monospace;
  padding: 2px 6px;
  border-radius: 4px;

  &::placeholder { color: rgba(255, 255, 255, 0.7); }
}

.field-count {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.85);
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.2);
  padding: 1px 6px;
  border-radius: 8px;
}

.node-body {
  padding: 0 0 4px;
}

.column-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  font-size: 12px;

  &:hover { background: $bg-light; }

  &.pk { background: rgba(245, 158, 11, 0.05); }
  &.fk { background: rgba(59, 130, 246, 0.05); }
  &.uk { background: rgba(99, 102, 241, 0.05); }
  &.ai-suggested {
    background: rgba(245, 158, 11, 0.08);
    border-left: 2px solid #F59E0B;
    padding-left: 8px;
  }
}

.col-key {
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}

.key-icon {
  font-size: 10px;

  &.pk { color: #F59E0B; }
  &.fk { color: #3B82F6; }
  &.uk { color: #6366F1; }
  &.ai { color: #F59E0B; }
}

.col-name {
  flex: 1;
  font-family: 'SF Mono', Consolas, monospace;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-type {
  font-size: 10px;
  color: $text-secondary;
  font-family: 'SF Mono', Consolas, monospace;
  font-weight: 500;

  &.type-numeric { color: #6366F1; }
  &.type-decimal { color: #8B5CF6; }
  &.type-string { color: #10B981; }
  &.type-time { color: #F59E0B; }
  &.type-binary { color: #EF4444; }
}

.more-fields {
  padding: 4px 10px;
  font-size: 11px;
  color: $text-placeholder;
  text-align: center;
  border-top: 1px dashed $border-light;
}

.column-footer {
  padding: 6px 10px;
  margin-top: 4px;
  font-size: 11px;
  color: $text-placeholder;
  border-top: 1px dashed $border-light;
  background: $bg-light;
}

.table-anchor {
  width: 12px !important;
  height: 12px !important;
  min-width: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  background: $primary-color !important;
  border: 2px solid white !important;
  border-radius: 50% !important;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 5;
  transform: translate(-50%, -50%);

  &:hover {
    opacity: 1 !important;
    transform: translate(-50%, -50%) scale(1.3);
  }

  &.top-anchor-left {
    top: 0px;
    left: 50%;
  }

  &.top-anchor-right {
    top: 0px;
    left: 50%;
  }

  &.bottom-anchor-left {
    bottom: -12px;
    left: 50%;
  }

  &.bottom-anchor-right {
    bottom: -12px;
    left: 50%;
  }

  &.side-anchor {
    &.left-target {
      left: 0;
      top: 50%;
      transform: translate(-50%, -50%);
    }

    &.left-source {
      left: 0;
      top: 50%;
      transform: translate(-50%, -50%);
    }

    &.right-target {
      right: 0;
      top: 50%;
      transform: translate(50%, -50%);
    }

    &.right-source {
      right: 0;
      top: 50%;
      transform: translate(50%, -50%);
    }
  }
}

html.dark {
  .table-node-wrap {
    background: #252526 !important;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.25), 0 4px 6px -4px rgba(0, 0, 0, 0.2) !important;

    &.selected {
      box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.25), 0 10px 15px -3px rgba(0, 0, 0, 0.25) !important;
    }
  }

  .column-row {
    &:hover {
      background: #3c3c3c !important;
    }

    &.pk { background: rgba(245, 158, 11, 0.12) !important; }
    &.fk { background: rgba(59, 130, 246, 0.12) !important; }
    &.uk { background: rgba(99, 102, 241, 0.12) !important; }
  }

  .col-name {
    color: #e2e8f0 !important;
  }

  .col-type {
    color: #94a3b8 !important;
  }

  .more-fields {
    color: #64748b !important;
    border-color: #3c3c3c !important;
  }

  .column-footer {
    color: #94a3b8 !important;
    border-color: #3c3c3c !important;
    background: #2a2a2b !important;
  }

  .table-anchor {
    border-color: #252526 !important;
  }
}
</style>
