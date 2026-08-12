import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import 'dayjs/locale/en'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './styles/global.scss'
import { useSettingsStore } from './stores/settings'

dayjs.extend(relativeTime)

const app = createApp(App)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(i18n)
app.use(ElementPlus)

const settingsStore = useSettingsStore(pinia)

// 等待设置加载完成后再挂载，保证刷新后设置值正确
;(async () => {
  await settingsStore.init()
  app.mount('#app')
})()
