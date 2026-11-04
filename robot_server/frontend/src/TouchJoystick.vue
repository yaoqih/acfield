<script setup lang="ts">
import { ref, watch } from 'vue'
import { Square } from 'lucide-vue-next'

const props = defineProps<{ disabled: boolean; active: boolean; connected: boolean }>()
const emit = defineEmits<{ move: [x: number, y: number]; stop: []; emergency: [] }>()
const stick = ref<HTMLElement | null>(null)
const x = ref(0)
const y = ref(0)
let pointer: number | null = null
const keys = new Set<string>()

function move(event: PointerEvent) {
  if (event.pointerId !== pointer || !stick.value) return
  const rect = stick.value.getBoundingClientRect()
  const radius = Math.min(rect.width, rect.height) * .36
  let dx = (event.clientX - rect.left - rect.width / 2) / radius
  let dy = (event.clientY - rect.top - rect.height / 2) / radius
  const length = Math.hypot(dx, dy)
  if (length > 1) { dx /= length; dy /= length }
  x.value = dx; y.value = dy
  emit('move', length < .12 ? 0 : dx, length < .12 ? 0 : -dy)
}
function start(event: PointerEvent) {
  if (props.disabled || pointer !== null || keys.size) return
  pointer = event.pointerId
  stick.value?.setPointerCapture(pointer)
  move(event)
}
function stop(event?: PointerEvent) {
  if (event && event.pointerId !== pointer) return
  if (pointer === null) return
  pointer = null; x.value = 0; y.value = 0
  emit('stop')
}
function updateKeys() {
  const dx = Number(keys.has('ArrowRight')) - Number(keys.has('ArrowLeft'))
  const dy = Number(keys.has('ArrowDown')) - Number(keys.has('ArrowUp'))
  const length = Math.max(1, Math.hypot(dx, dy))
  x.value = dx / length; y.value = dy / length
  emit('move', x.value, -y.value)
}
function keyMove(event: KeyboardEvent) {
  if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) return
  event.preventDefault()
  if (props.disabled || pointer !== null) return
  keys.add(event.key)
  updateKeys()
}
function keyStop(event?: KeyboardEvent) {
  if (!keys.size) return
  if (event) {
    if (!keys.has(event.key)) return
    event.preventDefault()
    keys.delete(event.key)
  } else keys.clear()
  if (keys.size) { updateKeys(); return }
  x.value = 0; y.value = 0
  emit('stop')
}
watch(() => [props.disabled, props.active], ([disabled, active]) => {
  if (disabled || !active) { pointer = null; keys.clear(); x.value = 0; y.value = 0 }
})
</script>

<template>
  <div class="touch-control">
    <div ref="stick" class="joystick" :class="{ disabled }" role="application" tabindex="0" aria-label="方向摇杆" :aria-disabled="disabled"
      @pointerdown.prevent="start" @pointermove.prevent="move" @pointerup="stop" @pointercancel="stop" @lostpointercapture="stop" @keydown="keyMove" @keyup="keyStop" @blur="keyStop()" @contextmenu.prevent>
      <span class="joystick-cross horizontal"></span><span class="joystick-cross vertical"></span>
      <span class="joystick-knob" :style="{ transform: `translate(${x * 66}px, ${y * 66}px)` }"></span>
    </div>
    <button class="touch-stop" type="button" :disabled="!connected" @click="emit('emergency')"><Square :size="16" fill="currentColor" />停车</button>
  </div>
</template>
