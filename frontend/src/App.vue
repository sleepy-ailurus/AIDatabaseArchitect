<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()
const { locale: i18nLocale } = useI18n()

const elementLocale = computed(() => {
  return settingsStore.language === 'zh-CN' ? zhCn : en
})

watch(
  () => settingsStore.language,
  (val) => {
    i18nLocale.value = val
    settingsStore.applyLanguage()
  },
  { immediate: true }
)
</script>

<style lang="scss">
#app {
  width: 100%;
  height: 100%;
}
</style>
