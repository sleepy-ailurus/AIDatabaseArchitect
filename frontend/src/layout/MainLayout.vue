<template>
  <div class="main-layout">
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="logo-section">
        <div class="logo-icon">
          <el-icon :size="28" color="#3B82F6"><DataBase /></el-icon>
        </div>
        <transition name="fade">
          <div v-if="!isCollapsed" class="logo-text">
            <div class="logo-title">AI DB Architect</div>
            <div class="logo-subtitle">数据库智能分析</div>
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
          text-color="#64748B"
          active-text-color="#3B82F6"
        >
          <template v-for="route in menuRoutes" :key="route.path">
            <el-menu-item :index="resolvePath(route.path)">
              <el-icon><component :is="route.meta.icon" /></el-icon>
              <template #title>{{ route.meta.title }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div class="sidebar-bottom">
        <el-tooltip v-if="!isCollapsed" content="设置" placement="right">
          <div class="settings-btn" :class="{ collapsed: isCollapsed }" @click="showSettings = true">
            <el-icon :size="20"><Setting /></el-icon>
            <transition name="fade">
              <span v-if="!isCollapsed" class="settings-label">设置</span>
            </transition>
          </div>
        </el-tooltip>
        <el-tooltip v-else content="设置" placement="right">
          <div class="settings-btn" :class="{ collapsed: isCollapsed }" @click="showSettings = true">
            <el-icon :size="20"><Setting /></el-icon>
            <transition name="fade">
              <span v-if="!isCollapsed" class="settings-label">设置</span>
            </transition>
          </div>
        </el-tooltip>
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
          <div class="search-box">
            <el-icon :size="14" color="#94A3B8"><Search /></el-icon>
            <input type="text" placeholder="搜索项目、数据库、表..." class="search-input" />
            <kbd class="shortcut-hint">Ctrl+K</kbd>
          </div>
        </div>

        <div class="header-right">
          <button class="icon-btn" title="通知">
            <el-badge :value="3" class="badge">
              <el-icon :size="17"><Bell /></el-icon>
            </el-badge>
          </button>
          <button class="icon-btn" title="设置" @click="showSettings = true">
            <el-icon :size="17"><Setting /></el-icon>
          </button>
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
      <SettingsDialog />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SettingsDialog from '@/components/SettingsDialog.vue'

const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const showSettings = ref(false)

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
  return route.meta?.title || 'AI DB Architect'
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
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.1));
  border-radius: 10px;
  flex-shrink: 0;
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
  gap: 8px;
  width: 100%;
  max-width: 440px;
  height: 34px;
  padding: 0 14px;
  background: $bg-light;
  border: 1px solid transparent;
  border-radius: 10px;
  transition: $transition-base;

  &:hover {
    background: #f1f5f9;
  }

  &:focus-within {
    background: $bg-white;
    border-color: $primary-color;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
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
