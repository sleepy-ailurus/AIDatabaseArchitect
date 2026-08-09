import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const STORAGE_KEY = 'aidb_settings'

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref('light')
  const language = ref('zh-CN')
  const systemDark = ref(false)

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

  const save = () => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        theme: theme.value,
        language: language.value
      }))
    } catch {}
  }

  const load = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const data = JSON.parse(raw)
        if (data.theme) theme.value = data.theme
        if (data.language) language.value = data.language
      }
    } catch {}
  }

  const init = () => {
    systemDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      systemDark.value = e.matches
      applyTheme()
    })
    load()
    applyTheme()
    applyLanguage()
  }

  watch([theme, language], save, { deep: true })

  return {
    theme,
    language,
    isDark,
    setTheme,
    setLanguage,
    applyTheme,
    applyLanguage,
    init
  }
})
