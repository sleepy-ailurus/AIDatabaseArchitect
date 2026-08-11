<template>
  <div class="main-layout">
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="logo-section">
        <div class="logo-icon">
          <img :src="logoImg" class="logo-img" alt="logo" />
        </div>
        <transition name="fade">
          <div v-if="!isCollapsed" class="logo-text">
            <div class="logo-title">{{ t('app.title') }}</div>
            <div class="logo-subtitle">{{ t('app.subtitle') }}</div>
          </div>
        </transition>
      </div>

      <el-scrollbar class="menu-scroll">
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapsed"
          :collapse-transition="false"
          router
          class="sidebar-menu"
          background-color="transparent"
          :text-color="menuTextColor"
          :active-text-color="menuActiveTextColor"
        >
          <template v-for="route in menuRoutes" :key="route.path">
            <el-menu-item :index="resolvePath(route.path)">
              <el-icon><component :is="route.meta.icon" /></el-icon>
              <template #title>{{ t(route.meta.title) }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div class="sidebar-bottom">
        <div class="settings-btn" :class="{ collapsed: isCollapsed }" @click="showSettings = true">
          <el-icon :size="20"><Setting /></el-icon>
          <transition name="fade">
            <span v-if="!isCollapsed" class="settings-label">{{ t('app.settings') }}</span>
          </transition>
        </div>
      </div>
    </aside>

    <div class="main-wrapper">
      <header class="header">
        <div class="header-left">
          <button class="icon-btn" @click="isCollapsed = !isCollapsed">
            <el-icon :size="18">
              <component :is="isCollapsed ? 'Expand' : 'Fold'" />
            </el-icon>
          </button>
          <div class="page-title">
            <span class="title-text">{{ currentPageTitle }}</span>
          </div>
        </div>

        <div class="header-center">
          <el-autocomplete
            v-model="searchQuery"
            :fetch-suggestions="fetchProjectSuggestions"
            :placeholder="t('app.searchPlaceholder')"
            :debounce="200"
            trigger-on-focus
            clearable
            class="search-box"
            popper-class="global-search-popper"
            @select="onProjectSelect"
            @keyup.enter="onSearchEnter"
          >
            <template #prefix>
              <el-icon :size="14" color="#94A3B8"><Search /></el-icon>
            </template>
            <template #default="{ item }">
              <div class="suggestion-item">
                <span class="suggestion-name">{{ item.name }}</span>
                <span class="suggestion-db">{{ item.db_type || 'MySQL' }}</span>
              </div>
            </template>
            <template #suffix>
              <kbd class="shortcut-hint">Ctrl+K</kbd>
            </template>
          </el-autocomplete>
        </div>
      </header>

      <main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <el-dialog
      v-model="showSettings"
      title=""
      width="700px"
      :close-on-click-modal="true"
      :show-close="true"
      custom-class="settings-dialog"
      align-center
      destroy-on-close
    >
      <SettingsDialog @close="showSettings = false" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import SettingsDialog from '@/components/SettingsDialog.vue'
import { useSettingsStore } from '@/stores/settings'
import { registerShortcut, unregisterShortcut } from '@/utils/shortcuts'
import { getProjects } from '@/api/project'
import logoImg from '@/resource/theme.png'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const settingsStore = useSettingsStore()

const isCollapsed = ref(false)
const showSettings = ref(false)
const searchQuery = ref('')

const handleNewProject = () => {
  router.push('/projects')
}

const handleOpenSettings = () => {
  showSettings.value = true
}

const fetchProjectSuggestions = async (query, cb) => {
  if (!query) {
    cb([])
    return
  }
  try {
    const data = await getProjects({ search: query, limit: 10 })
    const list = Array.isArray(data) ? data : (data?.items || data?.projects || [])
    cb(list.map(p => ({
      value: p.name,
      id: p.id,
      name: p.name,
      db_type: p.db_type || p.dbType || 'MySQL',
    })))
  } catch {
    cb([])
  }
}

const onProjectSelect = (item) => {
  if (item?.id) {
    searchQuery.value = ''
    router.push(`/projects/${item.id}/er-model`)
  }
}

const onSearchEnter = async () => {
  if (!searchQuery.value) return
  try {
    const data = await getProjects({ search: searchQuery.value, limit: 1 })
    const list = Array.isArray(data) ? data : (data?.items || data?.projects || [])
    if (list.length > 0) {
      searchQuery.value = ''
      router.push(`/projects/${list[0].id}/er-model`)
    }
  } catch {
    // silent fail
  }
}

const focusSearch = () => {
  nextTick(() => {
    const input = document.querySelector('.search-box input')
    if (input) input.focus()
  })
}

onMounted(() => {
  registerShortcut('Ctrl+n', handleNewProject)
  registerShortcut('Ctrl+,', handleOpenSettings)
  registerShortcut('Ctrl+k', focusSearch)
})

onBeforeUnmount(() => {
  unregisterShortcut('Ctrl+n')
  unregisterShortcut('Ctrl+,')
  unregisterShortcut('Ctrl+k')
})

const menuTextColor = computed(() => settingsStore.isDark ? '#94a3b8' : '#64748B')
const menuActiveTextColor = computed(() => settingsStore.isDark ? '#60a5fa' : '#3B82F6')

const menuRoutes = computed(() => {
  return router.options.routes[0].children.filter(r => !r.meta?.hidden)
})

const activeMenu = computed(() => {
  if (route.path.startsWith('/projects/')) {
    return '/projects'
  }
  return route.path
})

const currentPageTitle = computed(() => {
  if (route.meta?.title) {
    return t(route.meta.title)
  }
  return t('app.title')
})

const resolvePath = (path) => {
  return '/' + path
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.main-layout {
  display: flex;
  width: 100%;
  height: 100%;
  background: $bg-color;
}

.sidebar {
  width: $sidebar-width;
  background: $bg-white;
  border-right: 1px solid $border-light;
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  flex-shrink: 0;
  z-index: 10;

  &.collapsed {
    width: $sidebar-collapsed-width;
  }
}

.logo-section {
  height: $header-height;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid $border-light;
  gap: 12px;
  flex-shrink: 0;
}

.logo-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.1));
  border-radius: 10px;
  flex-shrink: 0;

  .logo-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 10px;
    display: block;
  }
}

.sidebar.collapsed .logo-icon {
  width: 32px;
  height: 32px;
}

.logo-text {
  overflow: hidden;
  white-space: nowrap;
}

.logo-title {
  font-size: 15px;
  font-weight: 700;
  color: $text-primary;
  letter-spacing: 0.2px;
}

.logo-subtitle {
  font-size: 11px;
  color: $text-secondary;
  margin-top: 1px;
}

.menu-scroll {
  flex: 1;
  padding: 12px 8px;
}

.sidebar-menu {
  border-right: none;

  :deep(.el-menu-item) {
    height: 44px;
    line-height: 44px;
    border-radius: 8px;
    margin-bottom: 2px;
    font-weight: 500;

    &:hover {
      background: $bg-light;
    }

    &.is-active {
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(99, 102, 241, 0.08));
      font-weight: 600;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 20px;
        background: $primary-color;
        border-radius: 0 2px 2px 0;
      }
    }
  }
}

.sidebar-bottom {
  padding: 10px 12px;
  border-top: 1px solid $border-light;
  flex-shrink: 0;
}

.settings-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  color: $text-secondary;
  transition: $transition-base;

  &:hover {
    background: $bg-light;
    color: $text-primary;
  }

  &.collapsed {
    justify-content: center;
    padding: 10px 0;
  }
}

.settings-label {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.header {
  height: $header-height;
  background: $bg-white;
  border-bottom: 1px solid $border-light;
  display: flex;
  align-items: center;
  padding: 0 0 0 16px;
  flex-shrink: 0;
  z-index: 5;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.icon-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 8px;
  color: $text-secondary;
  cursor: pointer;
  transition: $transition-base;

  &:hover {
    background: $bg-light;
    color: $text-primary;
  }

  .badge {
    :deep(.el-badge__content) {
      border: none;
      font-size: 10px;
      height: 16px;
      line-height: 16px;
      padding: 0 5px;
    }
  }
}

.page-title {
  display: flex;
  align-items: center;
  padding-left: 4px;

  .title-text {
    font-size: 14px;
    font-weight: 600;
    color: $text-primary;
    letter-spacing: 0.2px;
  }
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 0 24px;
  max-width: 520px;
}

.search-box {
  display: flex;
  align-items: center;
  width: 100%;
  max-width: 440px;
  height: 34px;

  :deep(.el-autocomplete__wrapper) {
    width: 100%;
    height: 34px;
    padding: 0 14px;
    background: $bg-light;
    border: 1px solid transparent;
    border-radius: 10px;
    transition: $transition-base;

    &:hover {
      background: #f1f5f9;
    }

    &.is-focus {
      background: $bg-white;
      border-color: $primary-color;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
  }

  :deep(.el-autocomplete__input) {
    flex: 1;
    border: none;
    background: transparent;
    outline: none;
    font-size: 13px;
    color: $text-primary;
    font-family: inherit;
    height: 32px;

    &::placeholder {
      color: $text-placeholder;
    }
  }

  :deep(.el-autocomplete__prefix) {
    display: flex;
    align-items: center;
  }
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 13px;
  color: $text-primary;
  font-family: inherit;

  &::placeholder {
    color: $text-placeholder;
  }
}

.shortcut-hint {
  font-size: 11px;
  color: $text-placeholder;
  background: $bg-color;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: inherit;
}

/* Suggestion item styling */
.suggestion-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.suggestion-name {
  font-size: 13px;
  color: $text-primary;
  font-weight: 500;
}

.suggestion-db {
  font-size: 11px;
  color: $text-secondary;
  background: $bg-light;
  padding: 1px 6px;
  border-radius: 4px;
}

.global-search-popper {
  :deep(.el-autocomplete-suggestion__list) {
    padding: 6px;
  }

  :deep(.el-autocomplete-suggestion__item) {
    padding: 8px 12px;
    border-radius: 6px;
    margin-bottom: 2px;

    &.is-checked {
      background: rgba(59, 130, 246, 0.08);
    }

    &:hover {
      background: $bg-light;
    }
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.main-content {
  flex: 1;
  overflow: hidden;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.25s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>

<style lang="scss">
html.dark {
  .main-layout {
    background: #252526 !important;
  }

  .sidebar {
    background: #252526 !important;
    border-color: #3c3c3c !important;
  }

  .logo-section {
    border-color: #3c3c3c !important;
  }

  .logo-title {
    color: #f8fafc !important;
  }

  .logo-subtitle {
    color: #94a3b8 !important;
  }

  .sidebar-menu.el-menu {
    --el-menu-hover-bg-color: #3c3c3c;
  }

  .sidebar-menu.el-menu .el-menu-item {
    &:hover {
      background: #3c3c3c !important;
    }

    &.is-active {
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(99, 102, 241, 0.15)) !important;

      &::before {
        background: #60a5fa !important;
      }
    }
  }

  .sidebar-bottom {
    border-color: #3c3c3c !important;
  }

  .settings-btn {
    color: #94a3b8 !important;

    &:hover {
      background: #3c3c3c !important;
      color: #f8fafc !important;
    }
  }

  .header {
    background: #252526 !important;
    border-color: #3c3c3c !important;
  }

  .page-title .title-text {
    color: #f8fafc !important;
  }

  .icon-btn {
    color: #94a3b8 !important;

    &:hover {
      background: #3c3c3c !important;
      color: #f8fafc !important;
    }
  }

  .search-box {
    :deep(.el-autocomplete__wrapper) {
      background: #3c3c3c !important;
      border-color: transparent !important;

      &:hover {
        background: #4a4a4a !important;
      }

      &.is-focus {
        background: #252526 !important;
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
      }
    }

    :deep(.el-autocomplete__input) {
      color: #f8fafc !important;

      &::placeholder {
        color: #94a3b8 !important;
      }
    }
  }

  .global-search-popper {
    background: #252526 !important;
    border-color: #3c3c3c !important;

    :deep(.el-autocomplete-suggestion__item) {
      color: #f8fafc !important;

      &:hover {
        background: #3c3c3c !important;
      }
    }
  }

  .shortcut-hint {
    background: #252526 !important;
    color: #94a3b8 !important;
  }
}

.settings-dialog.el-dialog {
  padding: 0 !important;
  overflow: hidden;
  border-radius: 14px;

  .el-dialog__header {
    display: none;
  }

  .el-dialog__body {
    padding: 0 !important;
    height: 560px !important;
    overflow: hidden !important;
  }

  .el-dialog__close {
    top: 12px;
    right: 16px;
    z-index: 10;
    color: #94A3B8;

    &:hover {
      color: #1E293B;
    }
  }
}
</style>
