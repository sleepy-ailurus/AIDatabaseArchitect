<template>
  <div class="chen-entity" :title="data.table">
    <div class="entity-name">{{ data.label }}</div>
    <div class="entity-sub" v-if="data.comment && data.comment !== data.label">{{ data.comment }}</div>
  </div>
</template>

<script setup>
defineProps({
  data: { type: Object, required: true }
})
</script>

<style scoped>
.chen-entity {
  width: 170px;
  min-height: 54px;
  background: #fff;
  border: 2px solid #3b82f6;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 10px;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);
  cursor: move;
}
.entity-name {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  text-align: center;
  line-height: 1.3;
}
.entity-sub {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
  text-align: center;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
