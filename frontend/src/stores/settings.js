import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getUserSettings, updateUserSettings } from '@/api/settings'

const STORAGE_KEY = 'aidb_settings'

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref('auto')
  const language = ref('zh-CN')
  const systemDark = ref(false)

  // AI 分析相关设置
  const showConfidence = ref(true)
  const autoCheckHigh = ref(true)

  // 是否已从后端加载完成（避免 watch 触发重复保存）
  const loaded = ref(false)
  // 防抖 timer
  let saveTimer = null

  const isDark = computed(() => {
    if (theme.value === 'dark') return true
    if (theme.value === 'light') return false
    return systemDark.value
  })

  const applyTheme = () => {
    const html = document.documentElement
    if (isDark.value) {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }
  }

  const applyLanguage = () => {
    document.documentElement.setAttribute('lang', language.value === 'zh-CN' ? 'zh-CN' : 'en')
  }

  const setTheme = (value) => {
    theme.value = value
    applyTheme()
  }

  const setLanguage = (value) => {
    language.value = value
    applyLanguage()
  }

  // 保存到后端（带防抖）
  const saveToBackend = () => {
    if (!loaded.value) return
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(async () => {
      try {
        await updateUserSettings({
          theme: theme.value,
          language: language.value,
          show_confidence: showConfidence.value,
          auto_check_high: autoCheckHigh.value,
        })
      } catch (e) {
        console.warn('保存设置到后端失败:', e)
        // 失败时 fallback 到 localStorage
        saveLocal()
      }
    }, 300)
  }

  const saveLocal = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        theme: theme.value,
        language: language.value,
        showConfidence: showConfidence.value,
        autoCheckHigh: autoCheckHigh.value,
      }))
    } catch {}
  }

  const loadLocal = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const data = JSON.parse(raw)
        if (data.theme) theme.value = data.theme
        if (data.language) language.value = data.language
        if (data.showConfidence !== undefined) showConfidence.value = data.showConfidence
        if (data.autoCheckHigh !== undefined) autoCheckHigh.value = data.autoCheckHigh
      }
    } catch {}
  }

  const loadFromBackend = async () => {
    try {
      const res = await getUserSettings()
      if (res) {
        theme.value = res.theme ?? theme.value
        language.value = res.language ?? language.value
        showConfidence.value = res.show_confidence ?? showConfidence.value
        autoCheckHigh.value = res.auto_check_high ?? autoCheckHigh.value
        // 加载成功后，同时同步一份到 localStorage 作为 fallback
        saveLocal()
      }
    } catch (e) {
      console.warn('从后端加载设置失败，使用本地存储:', e)
      loadLocal()
    } finally {
      loaded.value = true
    }
  }

  const init = async () => {
    systemDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      systemDark.value = e.matches
      applyTheme()
    })

    // 先快速加载本地缓存（避免 UI 闪烁）
    loadLocal()
    applyTheme()
    applyLanguage()

    // 再从后端加载（可能覆盖本地值）
    await loadFromBackend()
    applyTheme()
    applyLanguage()
  }

  // 监听变化，保存到后端
  watch(
    [theme, language, showConfidence, autoCheckHigh],
    () => {
      saveLocal() // 本地总是先存一份
      saveToBackend()
    },
    { deep: true }
  )

  return {
    theme,
    language,
    showConfidence,
    autoCheckHigh,
    isDark,
    setTheme,
    setLanguage,
    applyTheme,
    applyLanguage,
    init,
  }
})
