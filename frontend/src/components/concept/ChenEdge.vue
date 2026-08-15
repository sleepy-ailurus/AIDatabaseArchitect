<template>
  <BaseEdge :id="id" :path="path" :style="edgeStyle" />
  <EdgeLabelRenderer>
    <div
      v-if="label1"
      class="chen-card"
      :style="{ position: 'absolute', transform: `translate(-50%, -50%) translate(${label1.x}px, ${label1.y}px)` }"
    >
      {{ label1.text }}
    </div>
    <div
      v-if="label2"
      class="chen-card"
      :style="{ position: 'absolute', transform: `translate(-50%, -50%) translate(${label2.x}px, ${label2.y}px)` }"
    >
      {{ label2.text }}
    </div>
  </EdgeLabelRenderer>
</template>

<script setup>
import { computed } from 'vue'
import { BaseEdge, EdgeLabelRenderer, getBezierPath } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  sourceX: { type: Number, required: true },
  sourceY: { type: Number, required: true },
  targetX: { type: Number, required: true },
  targetY: { type: Number, required: true },
  sourcePosition: { type: String, default: 'top' },
  targetPosition: { type: String, default: 'bottom' },
  data: { type: Object, default: () => ({}) },
  markerEnd: { type: String, default: '' }
})

const path = computed(() => {
  const [d] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
    sourcePosition: props.sourcePosition,
    targetPosition: props.targetPosition
  })
  return d
})

const lerp = (a, b, t) => a + (b - a) * t

const label1 = computed(() => {
  const card = props.data?.sourceCard
  if (!card) return null
  return {
    text: card,
    x: lerp(props.sourceX, props.targetX, 0.22),
    y: lerp(props.sourceY, props.targetY, 0.22)
  }
})

const label2 = computed(() => {
  const card = props.data?.targetCard
  if (!card) return null
  return {
    text: card,
    x: lerp(props.sourceX, props.targetX, 0.78),
    y: lerp(props.sourceY, props.targetY, 0.78)
  }
})

const edgeStyle = computed(() => ({
  stroke: props.data?.junction ? '#10b981' : '#64748b',
  strokeWidth: props.data?.junction ? 2 : 1.5,
  strokeDasharray: props.data?.junction ? '6 3' : undefined
}))
</script>

<style scoped>
.chen-card {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  min-width: 18px;
  height: 18px;
  line-height: 16px;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  color: #334155;
  pointer-events: none;
  z-index: 5;
}
</style>
