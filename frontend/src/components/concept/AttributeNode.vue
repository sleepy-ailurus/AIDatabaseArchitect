<template>
  <div class="chen-attr" :class="{ pk: data.isPk, fk: data.isFk, uk: data.isUnique }">
    <span class="attr-text">{{ data.label }}</span>
  </div>
</template>

<script setup>
defineProps({
  data: { type: Object, required: true }
})
</script>

<style scoped>
.chen-attr {
  width: 108px;
  height: 34px;
  background: #f8fafc;
  border: 1.5px solid #94a3b8;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: move;
}
.chen-attr.pk {
  border-color: #d97706;
  background: #fffbeb;
}
.chen-attr.fk {
  border-color: #2563eb;
  background: #eff6ff;
}
.chen-attr.uk {
  border-color: #4f46e5;
  background: #eef2ff;
}
.attr-text {
  font-size: 11px;
  color: #334155;
  text-align: center;
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
