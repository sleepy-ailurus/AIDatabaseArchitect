<template>
  <g
    class="relation-edge-group"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <path
      v-if="isDark"
      :d="path"
      :stroke="edgeColor"
      stroke-width="5"
      stroke-linecap="round"
      stroke-linejoin="round"
      opacity="0.2"
      fill="none"
    />
    <path
      :d="path"
      :stroke="edgeColor"
      :stroke-width="isDark ? 2.5 : 2"
      :stroke-dasharray="isDashed ? '5,5' : 'none'"
      fill="none"
      stroke-linecap="round"
      stroke-linejoin="round"
    />

    <!-- Start decoration
         +x direction = away from table, into the line (after rotation)
         From line to table (decreasing +x): circle(+10) → crow V(+4) → crow tip(0) → table
    -->
    <g v-if="startMarkerType === 'tick'" :transform="startCrowTransform">
      <line x1="4" y1="-6" x2="4" y2="6" :stroke="edgeColor" stroke-width="2" stroke-linecap="round" />
      <line x1="8" y1="-6" x2="8" y2="6" :stroke="edgeColor" stroke-width="2" stroke-linecap="round" />
    </g>
    <g v-else-if="startMarkerType === 'crow'" :transform="startCrowTransform">
      <circle cx="10" cy="0" r="2.5" :fill="isDark ? '#1e1e1e' : 'white'" :stroke="edgeColor" stroke-width="1.8" />
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
      <circle cx="10" cy="0" r="2.5" :fill="isDark ? '#1e1e1e' : 'white'" :stroke="edgeColor" stroke-width="1.8" />
      <line x1="6" y1="0" x2="0" y2="-5" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
      <line x1="6" y1="0" x2="0" y2="0" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
      <line x1="6" y1="0" x2="0" y2="5" :stroke="edgeColor" stroke-width="1.8" stroke-linecap="round" />
    </g>

    <EdgeText
      v-if="showLabel && !showFkLabel"
      :x="labelX"
      :y="labelY"
      :label="labelText"
      :label-style="labelStyle"
      :label-show-bg="true"
      :label-bg-style="labelBgStyle"
    />

    <!-- FK constraint name label (database constraint only) -->
    <g
      v-if="showFkLabel"
      class="fk-label"
      style="pointer-events: none;"
      :transform="`translate(${fkLabelX}, ${fkLabelY})`"
    >
      <rect
        x="0"
        y="0"
        :width="fkLabelWidth"
        :height="fkLabelHeight"
        :fill="isDark ? '#2d2d2d' : '#ffffff'"
        :stroke="edgeColor"
        rx="4"
        stroke-width="1.5"
        :opacity="0.97"
      />
      <svg x="5" y="4" width="12" height="12" viewBox="0 0 24 24">
        <path
          d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"
          :stroke="edgeColor"
          stroke-width="2.2"
          stroke-linecap="round"
          stroke-linejoin="round"
          fill="none"
        />
      </svg>
      <text
        x="21"
        y="10"
        dominant-baseline="middle"
        :fill="isDark ? '#e2e8f0' : '#334155'"
        font-size="11"
        font-weight="600"
      >{{ constraintName }}</text>
    </g>

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
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { EdgeText, getSmoothStepPath } from '@vue-flow/core'

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
const isDark = ref(false)

let darkObserver = null
onMounted(() => {
  const html = document.documentElement
  isDark.value = html.classList.contains('dark')
  darkObserver = new MutationObserver(() => {
    isDark.value = html.classList.contains('dark')
  })
  darkObserver.observe(html, { attributes: true, attributeFilter: ['class'] })
})
onUnmounted(() => {
  darkObserver?.disconnect()
})

const sourceType = computed(() => props.data?.sourceType || 'database')

const edgeColor = computed(() => {
  // Only two visual categories now:
  //   - database constraint / explicit FK → blue
  //   - everything else (manual created, AI suggestion confirmed) → green
  //   - "suggested" (not yet approved) AI relationships are filtered out
  //     before reaching this component, so we never draw yellow dashed lines.
  const lightMap = {
    database: '#3B82F6',
    database_constraint: '#3B82F6',
    ai: '#10B981',
    ai_suggestion: '#10B981',
    ai_confirmed: '#10B981',
    manual: '#10B981'
  }
  const darkMap = {
    database: '#60a5fa',
    database_constraint: '#60a5fa',
    ai: '#34D399',
    ai_suggestion: '#34D399',
    ai_confirmed: '#34D399',
    manual: '#34D399'
  }
  const map = isDark.value ? darkMap : lightMap
  return map[sourceType.value] || (isDark.value ? '#60a5fa' : '#3B82F6')
})

const isDashed = computed(() => {
  // All visible lines are solid — suggested AI lines are filtered upstream.
  return false
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

const showLabel = computed(() => {
  // Confidence badges removed from the canvas — only the database FK name
  // should be overlaid on a line when applicable.
  return false
})

const constraintName = computed(() => props.data?.constraintName || '')
const isDatabaseConstraint = computed(() =>
  sourceType.value === 'database_constraint' ||
  sourceType.value === 'database' && constraintName.value
)
const showFkLabel = computed(() => isDatabaseConstraint.value && !!constraintName.value)

const FK_LABEL_HEIGHT = 20
const fkLabelWidth = computed(() => {
  const len = constraintName.value.length
  return Math.max(72, len * 6.5 + 30)
})
const fkLabelX = computed(() => labelX.value - fkLabelWidth.value / 2)
const fkLabelY = computed(() => labelY.value - FK_LABEL_HEIGHT - 6)

const labelText = computed(() => {
  const conf = props.data?.confidence
  if (conf !== undefined && conf < 1) {
    return `${(conf * 100).toFixed(0)}%`
  }
  return ''
})

const labelStyle = computed(() => ({
  fill: edgeColor.value,
  fontWeight: 700,
  fontSize: '11px'
}))

const labelBgStyle = computed(() => ({
  fill: isDark.value ? '#2d2d2d' : 'white',
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
    borderRadius: 4,
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
