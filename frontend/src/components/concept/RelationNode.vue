<template>
  <div class="chen-relation" @dblclick.stop="$emit('rename', data.id)">
    <div class="rel-shape">
      <span class="rel-name">{{ data.label }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  data: { type: Object, required: true }
})
defineEmits(['rename'])
</script>

<style scoped>
.chen-relation {
  width: 150px;
  height: 76px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: move;
}
.rel-shape {
  width: 96px;
  height: 96px;
  background: #ecfdf5;
  border: 2px solid #10b981;
  clip-path: polygon(50% 0, 100% 50%, 50% 100%, 0 50%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.rel-name {
  font-size: 13px;
  font-weight: 700;
  color: #065f46;
  text-align: center;
  max-width: 70px;
  line-height: 1.25;
  word-break: break-all;
}
</style>
