<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Activity, ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Battery, Camera, Check, ChevronDown, CircleHelp, Crosshair, Expand, Focus, Grid2X2, Layers, LockKeyhole, Maximize2, MousePointer2, Radio, Route, Settings2, ShieldCheck, Square, Unplug, UnlockKeyhole, Wifi, X } from 'lucide-vue-next'
import type { Robot, Settings, Snapshot } from './types'

const state = ref<Snapshot | null>(null)
const connected = ref(false)
const controlId = globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
const selectedId = ref('car-01')
const selected = computed(() => state.value?.robots.find(r => r.config.id === selectedId.value))
const online = computed(() => connected.value ? state.value?.robots.filter(r => r.online).length ?? 0 : 0)
const showTrails = ref(true)
const showBoxes = ref(true)
const showGrid = ref(true)
const expanded = ref(false)
const cameraOpen = ref(false)
const cameraFailed = ref(false)
const error = ref('')
const help = ref(false)
const settingsOpen = ref(false)
const draft = ref<Settings | null>(null)
const saving = ref(false)
const configError = ref('')
const originalConfig = ref('')
const discardPrompt = ref(false)
const notice = ref('')
const armPending = ref(false)
const detailPanel = ref<HTMLElement | null>(null)
const modalElement = ref<HTMLElement | null>(null)
const modalReturnFocus = ref<HTMLElement | null>(null)
let noticeTimer: ReturnType<typeof setTimeout> | undefined
const armedCount = computed(() => state.value?.robots.filter(r => r.armed || r.arm_pending).length ?? 0)
const dirty = computed(() => draft.value !== null && JSON.stringify(draft.value) !== originalConfig.value)
const duplicateTags = computed(() => draft.value ? new Set(draft.value.robots.map(r => r.tag_id)).size !== draft.value.robots.length : false)
const blockedReason = computed(() => {
  if (!connected.value) return '服务器连接中断，恢复后才能控制'
  if (state.value?.system_fault) return '控制服务故障，请重启服务'
  if (state.value?.estop) return '全局停止已锁定，请先释放全局停止'
  if (!selected.value) return '请先选择一辆小车'
  if (selected.value.fault) return `设备故障：${selected.value.fault}`
  if (!selected.value.online) return '设备离线，请检查小车电源与网络'
  if (!selected.value.bound) return '等待车端停车绑定确认'
  if (!selected.value.visible) return '定位不可用，请检查标签可见性与场地标定'
  if (selected.value.control_owner && selected.value.control_owner !== controlId) return '另一页面正在控制此车，请先锁定'
  if (selected.value.arm_pending) return '等待车端解锁确认'
  if (!selected.value.armed) return '准备就绪，点击「解锁控制」后即可操作'
  return ''
})
const canArm = computed(() => connected.value && !state.value?.estop && !state.value?.system_fault && selected.value?.online && selected.value.visible && selected.value.bound && !selected.value.fault && !selected.value.arm_pending && (!selected.value.control_owner || selected.value.control_owner === controlId))
function toast(message: string) {
  notice.value = message
  clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => notice.value = '', 3500)
}
async function toggleArm() {
  if (armPending.value || !selected.value) return
  const enabled = !selected.value.armed
  armPending.value = true
  endHold()
  try {
    const result = await api<{armed: boolean; pending: boolean}>(`/api/robots/${selectedId.value}/arm`, { enabled })
    toast(enabled ? result.pending ? '正在等待车端解锁确认' : '控制已解锁，按住方向按钮开始移动' : '小车已停车并锁定')
  } catch (e) { error.value = (e as Error).message }
  finally { armPending.value = false }
}
function closeSettings() {
  if (saving.value) return
  if (dirty.value) { discardPrompt.value = true; return }
  settingsOpen.value = false
  discardPrompt.value = false
}
async function lockForSettings() {
  try { await api('/api/stop'); toast('全车已锁定，可以保存配置') }
  catch (e) { configError.value = (e as Error).message }
}
function windowTop() { window.scrollTo({ top: 0, behavior: 'smooth' }) }
function focusControls() { detailPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }

const speed = ref(.08)
const turn = ref(.3)
const active = ref<string | null>(null)
const now = ref(Date.now())
const updated = ref(0)
let socket: WebSocket | null = null
let reconnect: ReturnType<typeof setTimeout> | undefined
let holdTimer: ReturnType<typeof setInterval> | undefined
let clockTimer: ReturnType<typeof setInterval> | undefined
let disposed = false
let generation = 0
let commandPending = false
let pendingRequest: Promise<unknown> = Promise.resolve()
const controlReady = computed(() => !blockedReason.value && !settingsOpen.value && !help.value)
const arena = computed(() => state.value?.arena ?? { width: 3, height: 3 })
const metric = (value: number | null | undefined, places = 2) => value == null ? '—' : value.toFixed(places)
const deg = (theta: number | null | undefined) => theta == null ? '—' : `${(theta * 180 / Math.PI).toFixed(1)}°`
const points = (xy: number[][]) => xy.map(p => `${p[0]},${p[1]}`).join(' ')
const clock = (t: number) => new Date(t * 1000).toLocaleTimeString('zh-CN', { hour12: false })
const commandLabel = (r: Robot) => ({ idle: '等待指令', sent: '已发送 · 等待确认', confirmed: '设备已确认', expired: '指令已过期' }[r.command_status] ?? r.command_status)

async function api<T>(path: string, body?: unknown, method = 'POST'): Promise<T> {
  const response = await fetch(path, { method, headers: { 'Content-Type': 'application/json', 'X-Control-ID': controlId }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(1500) })
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}))
    const message = Array.isArray(detail.detail)
      ? detail.detail.map((e: { loc: (string | number)[]; msg: string }) => `${e.loc.slice(1).join(' / ')}：${e.msg}`).join('；')
      : typeof detail.detail === 'string' ? detail.detail : '请求失败，请检查输入和服务连接'
    throw new Error(message)
  }
  return response.json()
}
async function action(path: string, body?: unknown) {
  try { await api(path, body); error.value = '' } catch (e) { error.value = (e as Error).message }
}
function connect() {
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
  socket.onmessage = event => {
    state.value = JSON.parse(event.data)
    updated.value = Date.now()
    connected.value = true
    if (!state.value?.robots.some(r => r.config.id === selectedId.value)) selectedId.value = state.value?.robots[0]?.config.id ?? ''
  }
  socket.onclose = () => {
    connected.value = false
    endHold()
    if (!disposed) reconnect = setTimeout(connect, 1500)
  }
  socket.onerror = () => socket?.close()
}
async function beginHold(direction: string, event?: PointerEvent) {
  if (!controlReady.value || active.value) return
  if (event) (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  const id = selectedId.value
  const token = ++generation
  active.value = direction
  const send = async () => {
    if (commandPending || token !== generation || !controlReady.value) return
    commandPending = true
    try {
      pendingRequest = api(`/api/robots/${id}/command`, {
        v: direction === 'up' ? speed.value : direction === 'down' ? -speed.value : 0,
        omega: direction === 'left' ? turn.value : direction === 'right' ? -turn.value : 0,
        ttl_ms: 300,
      })
      await pendingRequest
    } catch (e) { error.value = (e as Error).message; endHold() }
    finally { commandPending = false }
  }
  await send()
  if (active.value === direction && token === generation) holdTimer = setInterval(send, 90)
}
function endHold() {
  if (holdTimer) clearInterval(holdTimer)
  holdTimer = undefined
  const wasActive = active.value
  active.value = null
  generation++
  if (wasActive) {
    const id = selectedId.value
    // Send stop after any in-flight movement request, preserving command order.
    void pendingRequest.catch(() => {}).then(() => action(`/api/robots/${id}/command`, { v: 0, omega: 0, ttl_ms: 100 }))
  }
}
async function stopAll() { endHold(); await action('/api/stop') }
function select(id: string) { endHold(); selectedId.value = id }
async function openSettings() {
  endHold()
  try {
    draft.value = await api<Settings>('/api/config', undefined, 'GET')
    originalConfig.value = JSON.stringify(draft.value)
    configError.value = ''; discardPrompt.value = false; settingsOpen.value = true
  }
  catch (e) { error.value = (e as Error).message }
}
async function saveSettings() {
  if (armedCount.value || duplicateTags.value || saving.value) return
  configError.value = ''
  saving.value = true
  try {
    await api('/api/config', draft.value, 'PUT')
    settingsOpen.value = false
    toast('配置已保存，全车保持锁定')
  } catch (e) { configError.value = (e as Error).message }
  finally { saving.value = false }
}
function pageHidden() { if (document.hidden) endHold() }
function keydown(event: KeyboardEvent) {
  if (event.code === 'Escape') {
    endHold()
    if (settingsOpen.value) { if (discardPrompt.value) discardPrompt.value = false; else closeSettings() }
    else help.value = false
    return
  }
  if (event.code === 'Tab' && (settingsOpen.value || help.value)) {
    const focusable = Array.from(modalElement.value?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select, summary, [tabindex="0"]') ?? []).filter(el => el.getClientRects().length > 0)
    if (focusable?.length) {
      const first = focusable[0]!, last = focusable[focusable.length-1]!
      if (event.shiftKey && (document.activeElement === first || document.activeElement === modalElement.value)) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
  }
  if (event.code === 'Space' && !['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes((event.target as HTMLElement)?.tagName)) {
    event.preventDefault(); void stopAll()
  }
}
watch(controlReady, ready => { if (!ready) endHold() })
watch(() => settingsOpen.value || help.value, async open => {
  if (open) {
    endHold()
    modalReturnFocus.value = document.activeElement as HTMLElement
    document.body.style.overflow = 'hidden'
    await nextTick()
    modalElement.value?.focus()
  } else {
    document.body.style.overflow = ''
    modalReturnFocus.value?.focus()
  }
})
watch(() => [selected.value?.effective_max_v, selected.value?.effective_max_omega], () => {
  speed.value = Math.min(speed.value, selected.value?.effective_max_v ?? .1)
  turn.value = Math.min(turn.value, selected.value?.effective_max_omega ?? .3)
})
watch(selectedId, () => {
  speed.value = Math.min(speed.value, selected.value?.effective_max_v ?? .1)
  turn.value = Math.min(turn.value, selected.value?.effective_max_omega ?? .3)
})
onMounted(() => {
  connect()
  clockTimer = setInterval(() => {
    now.value = Date.now()
    if (updated.value && now.value - updated.value > 1500) { connected.value = false; endHold(); socket?.close() }
  }, 250)
  window.addEventListener('pointerup', endHold)
  window.addEventListener('pointercancel', endHold)
  window.addEventListener('blur', endHold)
  window.addEventListener('keydown', keydown)
  document.addEventListener('visibilitychange', pageHidden)
})
onUnmounted(() => {
  disposed = true; document.body.style.overflow = ''; clearTimeout(noticeTimer); endHold(); clearTimeout(reconnect); clearInterval(clockTimer); socket?.close()
  window.removeEventListener('pointerup', endHold); window.removeEventListener('pointercancel', endHold)
  window.removeEventListener('blur', endHold); window.removeEventListener('keydown', keydown)
  document.removeEventListener('visibilitychange', pageHidden)
})
</script>

<template>
  <div class="shell">
    <aside class="rail">
      <a class="brand-mark" href="/" aria-label="ACField 首页"><Focus :size="27" /></a>
      <button class="rail-button current" title="实验控制台" aria-label="实验控制台" @click="endHold(); expanded = false; windowTop()"><Grid2X2 :size="21" /></button>
      <button class="rail-button" title="设备与场地设置" aria-label="设备与场地设置" @click="openSettings"><Settings2 :size="21" /></button>
      <div class="rail-bottom"><button class="rail-button" aria-label="操作说明" title="操作说明" @click="help = true"><CircleHelp :size="21" /></button><span class="avatar" title="本地实验工作台">本地</span></div>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <div class="wordmark">ACField<span class="wordmark-dot">/</span></div>
        <span class="header-divider"></span><span class="workspace-name">多智能体实验室</span>
        <div class="top-right"><span class="connection" :class="{ off: !connected }"><i></i>{{ connected ? '服务器已连接' : '正在连接服务器' }}</span><span class="mono header-time">{{ new Date(now).toLocaleTimeString('zh-CN', { hour12: false }) }}</span></div>
      </header>
      <main>
        <section class="page-heading">
          <div><div class="eyebrow">WORKSPACE / LIVE CONTROL</div><h1>实验控制台 <span class="mode-tag">{{ !connected ? '连接未就绪' : state?.mode === 'hardware' ? '真实设备' : '模拟环境' }}</span></h1><p>观测场地，连接设备，让每一次协同清晰可见。</p></div>
          <div class="heading-actions"><button class="button subtle" @click="openSettings"><Settings2 :size="16" />实验配置</button><button class="button emergency" :disabled="!connected" @click="stopAll"><Square :size="13" fill="currentColor" />全局停止<span class="keycap">Space</span></button></div>
        </section>
        <div class="quick-start"><span><strong>{{ state?.mode === 'hardware' ? '真实设备' : '模拟体验' }}</strong>选择小车 → 解锁控制 → 按住方向按钮；松开即停车。</span><button @click="help = true">操作说明 <CircleHelp :size="14" /></button></div>
        <div v-if="!connected && state" class="error-banner" role="status">连接已中断，以下为最后一次收到的状态。正在自动重连…</div>
        <div v-if="error" class="error-banner" role="alert">{{ error }}<button aria-label="关闭提示" @click="error = ''"><X :size="16" /></button></div>
        <div v-if="state?.estop" class="stop-banner"><LockKeyhole :size="16" /><span>全局停止已锁定。释放后，小车仍需逐车解锁。</span><button :disabled="!connected" @click="action('/api/reset-stop')">释放全局停止 →</button></div>
        <section class="stats-row">
          <div class="stat"><span class="stat-icon green"><Radio :size="19" /></span><div><span class="stat-label">在线设备</span><div class="stat-value mono">{{ online }}<span>/ {{ state?.robots.length ?? 4 }}</span></div></div><span class="stat-note"><i :class="{ gray: !online }"></i>{{ online ? '链路正常' : '等待连接' }}</span></div>
          <div class="stat"><span class="stat-icon blue"><Crosshair :size="19" /></span><div><span class="stat-label">有效定位</span><div class="stat-value mono">{{ connected ? state?.robots.filter(r => r.visible).length ?? 0 : 0 }}<span>辆小车</span></div></div><span class="stat-note">{{ state?.mode === 'demo' ? '合成定位' : 'AprilTag' }}</span></div>
          <div class="stat"><span class="stat-icon amber"><Activity :size="19" /></span><div><span class="stat-label">最近更新</span><div class="stat-value mono">{{ connected ? metric(Math.max(0, now - updated), 0) : '—' }}<span>ms 前</span></div></div><span class="stat-note">{{ connected ? '实时同步' : '已断开' }}</span></div>
          <div class="stat"><span class="stat-icon neutral"><ShieldCheck :size="19" /></span><div><span class="stat-label">控制状态</span><div class="stat-value stat-text">{{ !connected ? '不可控制' : state?.estop ? '全局锁定' : '手动控制' }}</div></div><span class="stat-note">{{ state?.robots.filter(r => r.armed).length ?? 0 }} 辆已解锁</span></div>
        </section>
        <div class="main-grid" :class="{ expanded }">
          <section class="panel arena-panel">
            <div class="panel-header"><div class="panel-title"><span class="section-dot"></span>场地实时视图<span class="live-pill">LIVE</span></div><div class="panel-tools"><span class="mono arena-size">{{ arena.width.toFixed(1) }} × {{ arena.height.toFixed(1) }} m</span><button :class="{ toggled: showGrid }" :aria-pressed="showGrid" title="切换网格" aria-label="切换网格" @click="showGrid = !showGrid"><Grid2X2 :size="16" /></button><button :title="expanded ? '收起场地' : '展开场地'" :aria-label="expanded ? '收起场地' : '展开场地'" :aria-pressed="expanded" @click="expanded = !expanded"><Maximize2 :size="16" /></button></div></div>
            <div class="arena-toolbar"><div class="segmented"><button :aria-pressed="showTrails" :class="{ chosen: showTrails }" @click="showTrails = !showTrails"><Route :size="14" />运动轨迹</button><button :aria-pressed="showBoxes" :class="{ chosen: showBoxes }" @click="showBoxes = !showBoxes"><Layers :size="14" />车体轮廓</button></div><span><MousePointer2 :size="12" />点击小车查看详情</span></div>
            <div class="arena-canvas">
              <svg class="arena-svg" :viewBox="`-.24 -.22 ${arena.width + .48} ${arena.height + .46}`" role="img" aria-label="实时场地：小车位置、朝向及运动轨迹">
                <defs><pattern id="minor-grid" width=".1" height=".1" patternUnits="userSpaceOnUse"><circle cx="0" cy="0" r=".004" fill="#c5d2cb" /></pattern><pattern id="major-grid" width=".5" height=".5" patternUnits="userSpaceOnUse"><rect width=".5" height=".5" fill="url(#minor-grid)"/><path d="M .5 0 L 0 0 0 .5" fill="none" stroke="#d7dfd9" stroke-width=".005" /></pattern></defs>
                <rect x="0" y="0" :width="arena.width" :height="arena.height" rx=".015" :fill="showGrid ? 'url(#major-grid)' : '#f3f6f1'" stroke="#c1cec5" stroke-width=".009" />
                <g v-for="n in Math.floor(arena.width * 2) + 1" :key="`x${n}`"><text :x="(n-1)/2" :y="arena.height + .12" class="axis-text" text-anchor="middle">{{ ((n-1)/2).toFixed(1) }}</text></g>
                <g v-for="n in Math.floor(arena.height * 2) + 1" :key="`y${n}`"><text x="-.09" :y="arena.height - (n-1)/2 + .018" class="axis-text" text-anchor="end">{{ ((n-1)/2).toFixed(1) }}</text></g>
                <text :x="arena.width + .12" :y="arena.height + .12" class="axis-text">X / m</text><text x="-.17" y="-.09" class="axis-text">Y / m</text>
                <g v-for="(p, i) in [[0,0],[arena.width,0],[arena.width,arena.height],[0,arena.height]]" :key="`anchor${i}`" :transform="`translate(${p[0]},${arena.height - p[1]!})`"><rect x="-.035" y="-.035" width=".07" height=".07" rx=".008" fill="#fff" stroke="#84978a" stroke-width=".008"/><rect x="-.016" y="-.016" width=".032" height=".032" fill="#6b8073" /></g>
                <g :transform="`translate(0, ${arena.height}) scale(1,-1)`">
                  <template v-for="r in state?.robots" :key="r.config.id">
                    <polyline v-if="showTrails" :points="points(r.trail)" :stroke="r.config.color" fill="none" stroke-width=".012" stroke-linecap="round" opacity=".3" />
                    <g v-if="r.x !== null && r.y !== null" class="robot-marker" :opacity="r.visible && connected ? 1 : .35" tabindex="0" role="button" :aria-label="`选择${r.config.name}`" @click="select(r.config.id)" @keydown.enter="select(r.config.id)" @keydown.space.stop.prevent="select(r.config.id)">
                      <circle :cx="r.x" :cy="r.y" r=".23" fill="transparent" />
                      <circle v-if="selectedId === r.config.id" :cx="r.x" :cy="r.y" r=".205" :stroke="r.config.color" stroke-width=".006" stroke-dasharray=".025 .02" fill="none" opacity=".7" />
                      <polygon v-if="showBoxes" :points="points(r.corners)" :fill="r.config.color" fill-opacity=".13" :stroke="r.config.color" stroke-width=".009" stroke-linejoin="round" />
                      <g :transform="`translate(${r.x},${r.y}) rotate(${(r.theta ?? 0)*180/Math.PI})`"><rect x="-.06" y="-.055" width=".12" height=".11" rx=".025" :fill="r.config.color" /><path d="M .15 0 L .085 .04 L .085 -.04 Z" :fill="r.config.color"/><rect x="-.024" y="-.022" width=".044" height=".044" fill="white" opacity=".9" rx=".006"/><rect x="-.01" y="-.008" width=".018" height=".018" :fill="r.config.color"/></g>
                      <g :transform="`translate(${r.x},${r.y - .28}) scale(1,-1)`"><rect x="-.18" y="-.045" width=".36" height=".14" rx=".025" fill="white" stroke="#e3e8e2" stroke-width=".004"/><text x="0" y=".046" text-anchor="middle" class="robot-label">{{ r.config.id.toUpperCase() }}</text></g>
                    </g>
                  </template>
                </g>
              </svg>
              <div v-if="!connected" class="disconnected-overlay"><Unplug :size="22" /><strong>等待服务器连接</strong><span>连接恢复后将自动更新场地</span></div>
              <div class="map-badge"><span class="pulse-dot"></span>{{ state?.mode === 'demo' ? 'SIMULATION' : 'WORLD FRAME' }}</div>
            </div>
            <div class="arena-footer"><span><i class="legend-dot"></i>世界坐标系 · 米 / 弧度</span><span>{{ state?.mode === 'demo' ? '模拟数据 · 不发送硬件指令' : '定位超时 200 ms 自动锁定' }}</span><span class="mono">{{ connected ? '● 同步中' : '○ 离线' }}</span></div>
          </section>
          <aside ref="detailPanel" class="panel detail-panel" aria-label="选中设备与手动控制">
            <div class="panel-header"><div class="panel-title">设备详情</div><span class="small-label">{{ selected ? String(state?.robots.indexOf(selected)! + 1).padStart(2, '0') : '—' }} / {{ String(state?.robots.length ?? 0).padStart(2, '0') }}</span></div>
            <div class="robot-tabs"><button v-for="(r, i) in state?.robots" :key="r.config.id" :class="{ selected: selectedId === r.config.id }" :aria-pressed="selectedId === r.config.id" :aria-label="`选择设备 ${r.config.name}`" @click="select(r.config.id)"><i :style="{ background: r.config.color }"></i><span>{{ r.config.name }}</span><small>{{ connected && r.online ? '在线' : '离线' }}</small></button></div>
            <template v-if="selected">
              <div class="device-identity"><div class="device-symbol" :style="{ '--robot-color': selected.config.color }"><Focus :size="27" /></div><div><h2>{{ selected.config.name }}</h2><span class="mono">{{ selected.config.id.toUpperCase() }} <span class="muted">/ TAG {{ selected.config.tag_id }}</span></span></div><span class="online-label" :class="{ offline: !selected.online || !connected }"><i></i>{{ selected.online && connected ? '在线' : '离线' }}</span></div>
              <div class="device-status"><span><Wifi :size="13" />{{ selected.online && connected ? '通信正常' : '通信断开' }}</span><span><Crosshair :size="13" />{{ selected.visible && connected ? '定位有效' : '定位丢失' }}</span><span><Battery :size="15" />{{ metric(selected.battery, 0) }}%</span></div>
              <div class="position-summary"><span>X <b class="mono">{{ metric(selected.x, 2) }}</b> m</span><span>Y <b class="mono">{{ metric(selected.y, 2) }}</b> m</span><span><b class="mono">{{ deg(selected.theta) }}</b></span></div>
              <div class="control-heading"><h3>手动控制</h3><button class="lock-toggle" :class="{ armed: selected.armed }" :disabled="armPending || (!selected.armed && !canArm) || !connected" :title="blockedReason" @click="toggleArm"><UnlockKeyhole v-if="selected.armed" :size="12"/><LockKeyhole v-else :size="12" />{{ armPending || selected.arm_pending ? '确认中…' : selected.armed ? '锁定控制' : '解锁控制' }}</button></div>
              <p v-if="blockedReason" class="control-explanation" role="status">{{ blockedReason }}</p><div v-else class="control-explanation ready">控制已就绪 · 左右按钮为原地旋转</div>
              <div class="slider-row"><label for="speed">移动速度</label><input id="speed" v-model.number="speed" type="range" :min="Math.min(.02, selected.effective_max_v)" :max="selected.effective_max_v" step=".01" @input="endHold"><output class="mono">{{ speed.toFixed(2) }} <span>m/s</span></output></div>
              <div class="slider-row"><label for="turn">转向速度</label><input id="turn" v-model.number="turn" type="range" :min="Math.min(.1, selected.effective_max_omega)" :max="selected.effective_max_omega" step=".1" @input="endHold"><output class="mono">{{ turn.toFixed(1) }} <span>rad/s</span></output></div>
              <div class="dpad" @contextmenu.prevent>
                <button class="dpad-up" :class="{ pressed: active === 'up' }" :disabled="!controlReady" aria-label="按住前进" @pointerdown.prevent="beginHold('up', $event)" @keydown.enter.prevent="beginHold('up')" @keydown.space.prevent="beginHold('up')" @keyup.enter.prevent="endHold" @keyup.space.prevent="endHold" @blur="endHold" @lostpointercapture="endHold"><ArrowUp :size="20" /><span>前进</span></button>
                <button class="dpad-left" :class="{ pressed: active === 'left' }" :disabled="!controlReady" aria-label="按住左转" @pointerdown.prevent="beginHold('left', $event)" @keydown.enter.prevent="beginHold('left')" @keydown.space.prevent="beginHold('left')" @keyup.enter.prevent="endHold" @keyup.space.prevent="endHold" @blur="endHold" @lostpointercapture="endHold"><ArrowLeft :size="20" /><span>左转</span></button>
                <button class="dpad-stop" :disabled="!connected" aria-label="当前小车停车" @click="endHold(); action(`/api/robots/${selectedId}/command`, { v: 0, omega: 0, ttl_ms: 100 })"><Square :size="15" fill="currentColor" /></button>
                <button class="dpad-right" :class="{ pressed: active === 'right' }" :disabled="!controlReady" aria-label="按住右转" @pointerdown.prevent="beginHold('right', $event)" @keydown.enter.prevent="beginHold('right')" @keydown.space.prevent="beginHold('right')" @keyup.enter.prevent="endHold" @keyup.space.prevent="endHold" @blur="endHold" @lostpointercapture="endHold"><ArrowRight :size="20" /><span>右转</span></button>
                <button class="dpad-down" :class="{ pressed: active === 'down' }" :disabled="!controlReady" aria-label="按住后退" @pointerdown.prevent="beginHold('down', $event)" @keydown.enter.prevent="beginHold('down')" @keydown.space.prevent="beginHold('down')" @keyup.enter.prevent="endHold" @keyup.space.prevent="endHold" @blur="endHold" @lostpointercapture="endHold"><ArrowDown :size="20" /><span>后退</span></button>
              </div>
              <p class="control-hint">{{ selected.armed ? '按住方向按钮运行，松开即停车' : '解锁后，按住方向按钮控制小车' }}</p>
              <div class="command-state"><span class="command-dot" :class="{ on: selected.armed }"></span><span>{{ !connected ? '连接中断 · 暂停控制' : selected.reason }}</span><span class="mono">#{{ String(selected.seq).padStart(4, '0') }}</span></div><div class="ack-status">{{ commandLabel(selected) }} · 有效期 300 ms</div>
              <details class="telemetry-section"><summary>定位与速度详情<ChevronDown :size="14" /></summary>              <div class="telemetry-grid"><div><label>X 坐标 <span>m</span></label><strong class="mono">{{ metric(selected.x, 3) }}</strong></div><div><label>Y 坐标 <span>m</span></label><strong class="mono">{{ metric(selected.y, 3) }}</strong></div><div><label>车体朝向</label><strong class="mono">{{ deg(selected.theta) }}</strong></div><div><label>距上次定位 <span>ms</span></label><strong class="mono">{{ metric(selected.pose_age_ms, 0) }}</strong></div></div>
              <div class="velocity-row"><span>实测线速度<strong class="mono">{{ metric(selected.measured_v) }}<small> m/s</small></strong></span><span>视觉估计<strong class="mono">{{ metric(selected.estimated_v) }}<small> m/s</small></strong></span></div>
              <div class="extra-telemetry"><span>左 / 右编码计数 <b class="mono">{{ selected.encoder_left ?? '—' }} / {{ selected.encoder_right ?? '—' }}</b></span><span>电池电压 <b class="mono">{{ metric(selected.voltage_v, 2) }} V</b></span><span>实测角速度 <b class="mono">{{ metric(selected.measured_omega) }} rad/s</b></span><span>估计加速度 <b class="mono">{{ metric(selected.acceleration) }} m/s²</b></span></div>
</details>
            </template><div v-else class="waiting-device">等待设备状态…</div>
          </aside>
          <section class="panel camera-panel"><div class="panel-header"><div class="panel-title"><Camera :size="16" />视觉观察<span class="small-label">{{ state?.mode === 'demo' ? 'PREVIEW' : 'CAMERA' }}</span></div><button class="text-button" :disabled="!connected || state?.mode !== 'hardware' || !state.camera.connected" @click="cameraOpen = !cameraOpen; cameraFailed = false">{{ state?.mode !== 'hardware' ? '模拟模式无相机' : !state.camera.connected ? '等待相机连接' : cameraOpen ? '收起画面' : '展开画面' }}<Expand :size="13" /></button></div>
            <div v-if="cameraOpen && state?.mode === 'hardware' && state.camera.connected && !cameraFailed" class="camera-stream"><img :src="'/api/camera/stream'" alt="实时相机画面" @error="cameraFailed = true" /></div>
            <div v-else class="camera-placeholder"><div class="camera-illustration"><Camera :size="30" /><span class="camera-corner tl"></span><span class="camera-corner br"></span></div><div><h3>{{ state?.mode === 'demo' ? '先在模拟场地完成一次实验' : '连接你的俯视相机' }}</h3><p>{{ state?.mode === 'demo' ? '当前使用合成定位。接入 AprilTag 视觉服务后，可在此查看实时画面。' : cameraFailed ? '相机流暂时不可用，点击展开画面重试。' : state?.camera.reason }}</p></div><span class="camera-tag">{{ state?.camera.connected ? '已连接' : '未接入相机' }}</span></div>
          </section>
          <section class="panel events-panel"><div class="panel-header"><div class="panel-title"><Activity :size="16" />运行记录</div><span class="small-label">本次会话</span></div><div class="events-list"><div v-for="(event, index) in state?.events.slice(0, 4)" :key="`${event.time}-${index}`" class="event"><span class="mono">{{ clock(event.time) }}</span><i></i><span>{{ event.message }}</span></div><div v-if="!state?.events.length" class="empty-events">等待服务器事件</div></div></section>
        </div>
        <footer class="page-footer"><span><Focus :size="12" /> AClab <span class="footer-version">ACField · preview</span></span><span>本地实验工作台 <span>·</span> {{ state?.mode === 'demo' ? '模拟设备，不连接真实电机' : '局域网设备通信' }}</span><span class="mono">HTTP / WS / UDP</span></footer>
      </main>
    </div>
    <div v-if="notice" class="toast" role="status"><Check :size="17" />{{ notice }}</div>
    <button v-if="selected && !settingsOpen && !help" class="mobile-control-jump" @click="focusControls"><Focus :size="17" />{{ selected.config.name }} · 查看控制</button>
    <div v-if="settingsOpen && draft" class="modal-backdrop" @click.self="closeSettings"><section ref="modalElement" tabindex="-1" class="modal" role="dialog" aria-modal="true" aria-labelledby="settings-title"><div class="modal-header"><div><div class="eyebrow">EXPERIMENT SETTINGS</div><h2 id="settings-title">实验配置</h2></div><button aria-label="关闭配置" @click="closeSettings"><X :size="20" /></button></div><form @submit.prevent="saveSettings"><div class="modal-body"><p class="settings-note">调整场地和设备参数。保存后全车保持锁定，需要重新释放全局停止并解锁。</p><div v-if="armedCount" class="settings-warning"><span>{{ armedCount }} 辆小车尚未锁定，暂时不能保存。</span><button type="button" class="button subtle" :disabled="!connected" @click="lockForSettings">全车停车并锁定</button></div><p v-if="duplicateTags" class="modal-error" role="alert">AprilTag ID 不能重复，请为每辆小车分配不同的标签。</p><h3>场地尺寸</h3><div class="form-grid"><label>宽度 / m<input v-model.number="draft.arena_width" type="number" min="1" max="20" step=".1" required /></label><label>高度 / m<input v-model.number="draft.arena_height" type="number" min="1" max="20" step=".1" required /></label></div><details v-for="robot in draft.robots" :key="robot.id" class="robot-config" :open="robot.id === selectedId"><summary><i :style="{ background: robot.color }"></i>{{ robot.name }} <span class="mono">{{ robot.id.toUpperCase() }}</span><ChevronDown :size="14" /></summary><div class="form-grid"><label>设备名称<input v-model="robot.name" maxlength="40" required /></label><label>AprilTag ID<input v-model.number="robot.tag_id" type="number" min="0" max="65535" required /></label><label>标签边长 / m<input v-model.number="robot.tag_size" type="number" min=".001" max="1" step=".001" required /></label><label>显示颜色<input v-model="robot.color" type="color" /></label><label>车体长度 / m<input v-model.number="robot.length" type="number" min=".01" max="1" step=".01" required /></label><label>车体宽度 / m<input v-model.number="robot.width" type="number" min=".01" max="1" step=".01" required /></label><label>标签前向偏移 / m<input v-model.number="robot.tag_offset_x" type="number" min="-1" max="1" step=".001" required /></label><label>标签左向偏移 / m<input v-model.number="robot.tag_offset_y" type="number" min="-1" max="1" step=".001" required /></label><label>航向修正 / rad<input v-model.number="robot.heading_offset" type="number" min="-3.142" max="3.142" step=".001" required /></label><label>最大线速度 / m/s<input v-model.number="robot.max_v" type="number" min=".02" max="1" step=".01" required /></label><label>最大角速度 / rad/s<input v-model.number="robot.max_omega" type="number" min=".1" max="6" step=".1" required /></label></div><p class="field-note">标签偏移与航向需和视觉标定一致；标签边长不会自动同步到识别服务。</p></details></div><div v-if="configError" class="modal-error" role="alert">{{ configError }}</div><div v-if="discardPrompt" class="discard-prompt" role="alert"><span>有未保存的修改，是否放弃？</span><button type="button" @click="discardPrompt = false">继续编辑</button><button type="button" @click="settingsOpen = false; discardPrompt = false">放弃修改</button></div><div class="modal-footer"><span class="save-state">{{ saving ? '正在保存…' : dirty ? '有未保存的修改' : '配置未修改' }}</span><button type="button" class="button subtle" @click="closeSettings">取消</button><button type="submit" class="button primary" :disabled="saving || !connected || armedCount > 0 || duplicateTags || !dirty"><Check :size="16" />{{ saving ? '保存中…' : '保存配置' }}</button></div></form></section></div>
    <div v-if="help" class="modal-backdrop" @click.self="help = false"><section ref="modalElement" tabindex="-1" class="modal help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title"><div class="modal-header"><h2 id="help-title">开始一次实验</h2><button aria-label="关闭操作说明" @click="help = false"><X :size="20" /></button></div><div class="modal-body"><ol><li>确认顶部为模拟环境或预期的真实设备模式。</li><li>在场地或设备标签中选择一辆小车。</li><li>确认通信与定位有效，点击「解锁」。</li><li>按住方向按钮运行，松开后停车；左右按钮原地旋转。键盘可用 Tab 聚焦方向按钮，按住回车或空格操作。</li><li>按空格或点击「全局停止」锁定全部设备。</li></ol><p>真实设备需要实现 UDP 协议和独立的车端超时停车。已加入保守的边界与车间距离停车保护，仍需实测定位误差和停止距离；它不会自动规划绕行。故障或指令超时后需重新解锁。</p><p>标签尺寸用于记录；识别端的标签尺寸和世界坐标标定仍需在 AprilTag 服务中配置。</p></div></section></div>
  </div>
</template>
