<template>
  <el-dialog
    v-model="visible"
    :title="t('importSchema.title')"
    width="760px"
    destroy-on-close
    align-center
  >
    <el-tabs v-model="source">
      <el-tab-pane :label="t('importSchema.ddl')" name="ddl">
        <el-input
          v-model="content"
          type="textarea"
          :rows="10"
          :placeholder="t('importSchema.ddlPlaceholder')"
          class="code-input"
        />
      </el-tab-pane>
      <el-tab-pane :label="t('importSchema.dbml')" name="dbml">
        <el-input
          v-model="content"
          type="textarea"
          :rows="10"
          :placeholder="t('importSchema.dbmlPlaceholder')"
          class="code-input"
        />
      </el-tab-pane>
    </el-tabs>

    <div class="tool-row">
      <el-upload
        :auto-upload="false"
        :show-file-list="false"
        accept=".sql,.dbml,.txt"
        :on-change="onFileChange"
      >
        <el-button :icon="Upload">{{ t('importSchema.chooseFile') }}</el-button>
      </el-upload>
      <span class="hint">{{ t('importSchema.noDbNeeded') }}</span>
    </div>

    <div v-if="preview" class="preview-block">
      <div class="preview-title">
        {{ t('importSchema.previewTitle') }}
        <span class="preview-count">{{ preview.table_count }} {{ t('importSchema.tables') }} · {{ preview.relationship_count }} {{ t('importSchema.fks') }}</span>
      </div>
      <el-table :data="preview.tables" size="small" max-height="220">
        <el-table-column prop="name" :label="t('importSchema.tableName')" min-width="160" />
        <el-table-column prop="comment" :label="t('importSchema.comment')" min-width="140">
          <template #default="{ row }">{{ row.comment || '-' }}</template>
        </el-table-column>
        <el-table-column :label="t('importSchema.columns')" width="80" align="center">
          <template #default="{ row }">{{ row.columns?.length || 0 }}</template>
        </el-table-column>
        <el-table-column :label="t('importSchema.fks')" width="80" align="center">
          <template #default="{ row }">{{ row.foreign_keys?.length || 0 }}</template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button :loading="previewing" @click="doPreview">{{ t('importSchema.preview') }}</el-button>
      <el-button type="primary" :loading="importing" :disabled="!preview" @click="doImport">
        {{ t('importSchema.import') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { previewImport, importSchema } from '@/api/schemaImport'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  projectId: { type: [String, Number], required: true }
})
const emit = defineEmits(['update:modelValue', 'imported'])
const { t } = useI18n()

const visible = ref(false)
const source = ref('ddl')
const content = ref('')
const preview = ref(null)
const previewing = ref(false)
const importing = ref(false)

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val) {
      source.value = 'ddl'
      content.value = ''
      preview.value = null
    }
  }
)
watch(visible, (val) => emit('update:modelValue', val))

const onFileChange = (file) => {
  const raw = file.raw
  if (!raw) return
  const reader = new FileReader()
  reader.onload = () => {
    content.value = String(reader.result || '')
    source.value = /\.dbml$/i.test(raw.name) ? 'dbml' : 'ddl'
    preview.value = null
  }
  reader.readAsText(raw)
}

const doPreview = async () => {
  if (!content.value.trim()) {
    ElMessage.warning(t('importSchema.enterContent'))
    return
  }
  previewing.value = true
  try {
    preview.value = await previewImport(props.projectId, {
      source: source.value,
      content: content.value
    })
  } catch {
    preview.value = null
  } finally {
    previewing.value = false
  }
}

const doImport = async () => {
  importing.value = true
  try {
    const res = await importSchema(props.projectId, {
      source: source.value,
      content: content.value
    })
    ElMessage.success(res?.message || t('importSchema.imported'))
    visible.value = false
    emit('imported')
  } catch {
    // interceptor shows error
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.code-input {
  font-family: 'SF Mono', Consolas, monospace;
  font-size: 12px;
}
.tool-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}
.hint {
  font-size: 12px;
  color: #94a3b8;
}
.preview-block {
  margin-top: 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}
.preview-title {
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
}
.preview-count {
  font-weight: 400;
  color: #64748b;
  font-size: 12px;
}
</style>
