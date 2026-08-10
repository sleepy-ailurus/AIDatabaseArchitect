import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  fallbackLocale: 'en-US',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS
  }
})

// Message lookup table for dynamic data translations
const localeMap = {
  'zh-CN': zhCN,
  'en-US': enUS
}

/**
 * Translate a dynamic data value using the data mapping dictionaries.
 * Falls back to the original value if no mapping is found.
 * @param {string} category - 'projectNames' | 'reasons'
 * @param {string} value - The original Chinese value from backend
 * @returns {string} Translated value or original value
 */
export function translateData(category, value) {
  if (!value) return value
  const locale = i18n.global.locale.value
  const localeData = localeMap[locale] || localeMap[i18n.global.fallbackLocale.value]
  if (localeData?.data?.[category]?.[value]) {
    return localeData.data[category][value]
  }
  // Try fallback locale
  const fallbackData = localeMap[i18n.global.fallbackLocale.value]
  if (fallbackData?.data?.[category]?.[value]) {
    return fallbackData.data[category][value]
  }
  return value
}

/**
 * Vue composable for dynamic data translation.
 * Use in components: const { tData } = useDataI18n()
 */
export function useDataI18n() {
  const tData = (category, value) => translateData(category, value)
  return { tData }
}

export default i18n
