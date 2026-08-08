<template>
  <g
    class="relation-edge-group"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <path :d="path" :style="edgePathStyle" />

    <!-- Start decoration
         +x direction = away from table, into the line (after rotation)
         From line to table (decreasing +x): circle(+10) → crow V(+4) → crow tip(0) → table
    -->
    <g v-if="startMarkerType === 'tick'" :transform="startCrowTransform">
      <line x1="4" y1="-6" x2="4" y2="6" :stroke="edgeColor" stroke-width="2" stroke-linecap="round" />
      <line x1="8" y1="-6" x2="8" y2="6" :stroke="edgeColor" stroke-width="2" stroke-linecap="round" />
    </g>
    <g v-else-if="startMarkerType === 'crow'" :transform="startCrowTransform">
      <circle cx="10" cy="0" r="2.5" fill="white" :stroke="edgeColor" stroke-width="1.8" />
      <line x1="4" y1="0" x2="0" y2="-5" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
      <line x1="4" y1="0" x2="0" y2="0" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
      <line x1="4" y1="0" x2="0" y2="5" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
    </g>

    <!-- End decoration -->
    <g v-if="endMarkerType === 'tick'" :transform="endCrowTransform">
      <line x1="4" y1="-6" x2="4" y2="6" :stroke="edgeColor" stroke-width="2" stroke-linecap="round" />
      <line x1="8" y1="-6" x2="8" y2="6" :stroke="edgeColor" stroke-width="2" stroke-linecap="round" />
    </g>
    <g v-else-if="endMarkerType === 'crow'" :transform="endCrowTransform">
      <circle cx="10" cy="0" r="2.5" fill="white" :stroke="edgeColor" stroke-width="1.8" />
      <line x1="6" y1="0" x2="0" y2="-5" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
      <line x1="6" y1="0" x2="0" y2="0" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
      <line x1="6" y1="0" x2="0" y2="5" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
    </g>

    <EdgeText
      v-if="showLabel"
      :x="labelX"
      :y="labelY"
      :label="labelText"
      :label-style="labelStyle"
      :label-show-bg="true"
      :label-bg-style="labelBgStyle"
    />
    <div
      v-if="hovered"
      class="edge-delete-btn"
      :style="{ left: labelX + 'px', top: labelY + 'px' }"
      @click.stop="handleDelete"
    >
      <el-icon :size="12"><Close /></el-icon>
    </div>
  </g>
</template>

<script setup>
import { computed, ref } from 'vue'
import { BaseEdge, EdgeText, getSmoothStepPath } from '@vue-flow/core'

const props = defineProps({
  id: { type: String, required: true },
  sourceX: { type: Number, required: true },
  sourceY: { type: Number, required: true },
  targetX: { type: Number, required: true },
  targetY: { type: Number, required: true },
  sourcePosition: { type: String, default: 'right' },
  targetPosition: { type: String, default: 'left' },
  data: { type: Object, default: () => ({}) },
  markerEnd: { type: String, default: '' },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['delete'])

const hovered = ref(false)

const sourceType = computed(() => props.data?.sourceType || 'database')

const edgeColor = computed(() => {
  const map = {
    database: '#3B82F6',
    database_constraint: '#3B82F6',
    ai: '#F59E0B',
    ai_suggestion: '#F59E0B',
    ai_confirmed: '#10B981',
    manual: '#10B981'
  }
  return map[sourceType.value] || '#3B82F6'
})

const isDashed = computed(() => {
  const t = sourceType.value
  return t === 'ai' || t === 'ai_suggestion'
})

const cardinality = computed(() => props.data?.cardinality || '1:N')

const startMarkerType = computed(() => {
  const card = cardinality.value
  const first = card.split(':')[0]
  return first === '1' ? 'tick' : 'crow'
})

const endMarkerType = computed(() => {
  const card = cardinality.value
  const second = card.split(':')[1]
  return second === '1' ? 'tick' : 'crow'
})

const edgePathStyle = computed(() => ({
  stroke: edgeColor.value,
  strokeWidth: 2,
  strokeDasharray: isDashed.value ? '5,5' : 'none',
  fill: 'none'
}))

const showLabel = computed(() => {
  return !!props.data?.cardinality || !!props.data?.confidence
})

const labelText = computed(() => {
  const card = props.data?.cardinality || '1:N'
  const conf = props.data?.confidence
  if (conf !== undefined && conf < 1) {
    return `${card} · ${(conf * 100).toFixed(0)}%`
  }
  return card
})

const labelStyle = computed(() => ({
  fill: edgeColor.value,
  fontWeight: 700,
  fontSize: '11px'
}))

const labelBgStyle = computed(() => ({
  fill: 'white',
  padding: '2px 5px',
  rx: 4
}))

const pathComputed = computed(() => {
  return getSmoothStepPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
    borderRadius: 10,
    // offset = distance the line endpoint sits back FROM the handle (into the line)
    // Decorations are drawn from handle center (0,0) outward into the line (+x, 0 to 10px)
    // This offset must be >= max decoration extent (crow tip at x=0 handle, circle at x=10)
    offset: 12
  })
})

const path = computed(() => pathComputed.value[0])
const labelX = computed(() => pathComputed.value[1])
const labelY = computed(() => pathComputed.value[2])

// Angle mapping: rotate so local +x points AWAY from the handle (into the line)
// Handle position on the side of the node → line goes outward from that side → that's the +x direction
const directionAngle = (position) => {
  switch (position) {
    case 'right': return 0
    case 'left': return 180
    case 'bottom': return 90
    case 'top': return -90
    default: return 0
  }
}

const sourceAngle = computed(() => directionAngle(props.sourcePosition))
const targetAngle = computed(() => directionAngle(props.targetPosition))

const startCrowTransform = computed(() =>
  `translate(${props.sourceX}, ${props.sourceY}) rotate(${sourceAngle.value})`
)
const endCrowTransform = computed(() =>
  `translate(${props.targetX}, ${props.targetY}) rotate(${targetAngle.value})`
)

const handleDelete = () => {
  emit('delete', props.id)
}
</script>

<script>
export default {
  inheritAttrs: false
}
</script>

<style lang="scss">
.edge-delete-btn {
  position: absolute;
  transform: translate(-50%, -50%);
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #EF4444;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  pointer-events: all;
  z-index: 10;
  box-shadow: 0 2px 6px rgba(239, 68, 68, 0.4);

  &:hover {
    background: #DC2626;
    transform: translate(-50%, -50%) scale(1.15);
  }
}
</style>
