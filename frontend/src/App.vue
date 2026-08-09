<template>
  <el-config-provider :locale="locale">
    <router-view />
  </el-config-provider>
</template>

<script setup>
import { computed, watch } from 'vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import en from 'element-plus/es/locale/lang/en'
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()

const locale = computed(() => {
  return settingsStore.language === 'zh-CN' ? zhCn : en
})

watch(locale, () => {
  settingsStore.applyLanguage()
})
</script>

<style lang="scss">
#app {
  width: 100%;
  height: 100%;
}
</style>
