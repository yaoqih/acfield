<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { Activity, Battery, Camera, Check, ChevronDown, CircleHelp, Crosshair, Expand, Focus, Grid2X2, Layers, LockKeyhole, Maximize2, MousePointer2, Plus, Radio, Route, Settings2, ShieldCheck, Smartphone, Square, Trash2, Unplug, UnlockKeyhole, Wifi, X } from 'lucide-vue-next'
import type { Robot, RobotConfig, Settings, Snapshot, VisionProfile, VisionResponse, VisionStatus } from './types'
import CameraSettings from './CameraSettings.vue'
import TouchJoystick from './TouchJoystick.vue'

const state = ref<Snapshot | null>(null)
const mobilePage = location.pathname === '/mobile' || location.pathname === '/mobile/'
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
const addedRobotIndex = ref(-1)
const settingsSection = ref('robots')
const saving = ref(false)
const configError = ref('')
const originalConfig = ref('')
const visionProfile = ref<VisionProfile | null>(null)
const visionStatus = ref<VisionStatus | null>(null)
const originalVision = ref('')
const visionError = ref('')
const visionBusy = ref(false)
const visionNeedsSync = ref(false)
const cameraDevices = ref<{id: string; name: string}[]>([])
const streamKey = ref(0)
const loadedVisionUrl = ref('')
const profileJson = (profile: VisionProfile | null) => JSON.stringify(profile ? { ...profile, saved_world: undefined } : null)
const discardPrompt = ref(false)
const notice = ref('')
const armPending = ref(false)
const modePending = ref(false)
const detailPanel = ref<HTMLElement | null>(null)
const detailVisible = ref(false)
const modalElement = ref<HTMLElement | null>(null)
const modalReturnFocus = ref<HTMLElement | null>(null)
let noticeTimer: ReturnType<typeof setTimeout> | undefined
const armedCount = computed(() => state.value?.robots.filter(r => r.armed || r.arm_pending).length ?? 0)
const dirty = computed(() => draft.value !== null && (visionNeedsSync.value || JSON.stringify(draft.value) !== originalConfig.value || profileJson(visionProfile.value) !== originalVision.value))
const duplicateTags = computed(() => draft.value ? new Set(draft.value.robots.map(r => r.tag_id)).size !== draft.value.robots.length : false)
const duplicateIds = computed(() => draft.value ? new Set(draft.value.robots.map(r => r.id)).size !== draft.value.robots.length : false)
async function addRobot() {
  if (!draft.value || draft.value.robots.length >= 16) return
  const ids = new Set(draft.value.robots.map(r => r.id))
  const tags = new Set([...draft.value.robots.map(r => r.tag_id), ...Object.entries(visionProfile.value?.tags ?? {}).filter(([, tag]) => tag.role === 'fixed').map(([id]) => Number(id))])
  let index = 1
  while (ids.has(`car-${String(index).padStart(2, '0')}`)) index++
  const tagId = Array.from({ length: 587 }, (_, i) => i).find(id => !tags.has(id))
  if (tagId === undefined) { configError.value = '没有可用的 AprilTag ID'; return }
  const robot: RobotConfig = { id: `car-${String(index).padStart(2, '0')}`, name: `小车 ${index}`, tag_id: tagId, color: ['#28786b', '#427dc2', '#ac7b35', '#ba6070'][draft.value.robots.length % 4]!, tag_size: .104, tag_height: .0646, length: .20, width: .16, body_offset_x: 0, body_offset_y: 0, tag_offset_x: 0, tag_offset_y: 0, heading_offset: 0, max_v: .10, max_omega: .30 }
  draft.value.robots.push(robot)
  addedRobotIndex.value = draft.value.robots.length - 1
  configError.value = ''
  await nextTick()
  modalElement.value?.querySelector('.robot-config:last-of-type')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}
function removeRobot(index: number) {
  if (!draft.value || draft.value.robots.length <= 1) return
  const robot = draft.value.robots[index]
  if (robot && window.confirm(`删除 ${robot.name}（${robot.id}）？保存配置后生效。`)) draft.value.robots.splice(index, 1)
}
function showSettingsSection(section: string) {
  settingsSection.value = section
  modalElement.value?.querySelector(`#settings-${section}`)?.scrollIntoView({ block: 'start', behavior: 'smooth' })
}
function trackSettingsSection(event: Event) {
  const body = event.currentTarget as HTMLElement
  const top = body.getBoundingClientRect().top + 40
  for (const section of ['camera', 'arena', 'robots']) {
    const element = body.querySelector(`#settings-${section}`)
    if (element && element.getBoundingClientRect().top <= top) { settingsSection.value = section; return }
  }
  settingsSection.value = 'robots'
}
function revealInvalid(event: Event) {
  let element = (event.target as HTMLElement).parentElement
  while (element && element !== modalElement.value) {
    if (element instanceof HTMLDetailsElement) element.open = true
    element = element.parentElement
  }
}
const blockedReason = computed(() => {
  if (!connected.value) return '服务器连接中断，恢复后才能控制'
  if (state.value?.system_fault) return '控制服务故障，请重启服务'
  if (state.value?.estop) return '全局停止已锁定，请先释放全局停止'
  if (!selected.value) return '请先选择一辆小车'
  if (selected.value.fault) return `设备故障：${selected.value.fault}`
  if (!selected.value.online) return '设备离线，请检查小车电源与网络'
  if (!selected.value.bound) return '等待车端停车绑定确认'
  if (!selected.value.visible && !state.value?.allow_unlocalized_control) return '定位不可用，请检查标签可见性与场地标定'
  if (selected.value.control_owner && selected.value.control_owner !== controlId) return '另一页面正在控制此车，请先锁定'
  if (selected.value.arm_pending) return '等待车端解锁确认'
  if (!selected.value.armed) return '准备就绪，点击「解锁控制」后即可操作'
  return ''
})
const canArm = computed(() => connected.value && !state.value?.estop && !state.value?.system_fault && selected.value?.online && (state.value?.allow_unlocalized_control || selected.value.visible) && selected.value.bound && !selected.value.fault && !selected.value.arm_pending && (!selected.value.control_owner || selected.value.control_owner === controlId))
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
    toast(enabled ? result.pending ? '正在等待车端解锁确认' : '控制已解锁' : '小车已停车并锁定')
  } catch (e) { error.value = (e as Error).message }
  finally { armPending.value = false }
}
function closeSettings() {
  if (saving.value || visionBusy.value) return
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

const active = ref<string | null>(null)
const joystick = ref({ x: 0, y: 0 })
const stopping = ref(false)
const now = ref(Date.now())
const updated = ref(0)
let socket: WebSocket | null = null
let reconnect: ReturnType<typeof setTimeout> | undefined
let holdTimer: ReturnType<typeof setInterval> | undefined
let clockTimer: ReturnType<typeof setInterval> | undefined
let visionTimer: ReturnType<typeof setInterval> | undefined
let visionPollPending = false
let disposed = false
let generation = 0
let commandPending = false
let pendingRequest: Promise<unknown> = Promise.resolve()
let detailObserver: IntersectionObserver | undefined
const controlReady = computed(() => !blockedReason.value && !settingsOpen.value && !help.value && !modePending.value && !stopping.value)
const arena = computed(() => state.value?.arena ?? { width: 3, height: 3 })
const metric = (value: number | null | undefined, places = 2) => value == null ? '—' : value.toFixed(places)
const deg = (theta: number | null | undefined) => theta == null ? '—' : `${(theta * 180 / Math.PI).toFixed(1)}°`
const points = (xy: number[][]) => xy.map(p => `${p[0]},${p[1]}`).join(' ')
const clock = (t: number) => new Date(t * 1000).toLocaleTimeString('zh-CN', { hour12: false })
const commandLabel = (r: Robot) => ({ idle: '等待指令', sent: '已发送 · 等待确认', confirmed: '设备已确认', expired: '指令已过期' }[r.command_status] ?? r.command_status)

// Use the measured pack voltage for the 3S estimate; simulator percentage remains a fallback.
const batteryCurve: [number, number][] = [[10.5, 0], [10.8, 5], [11.1, 10], [11.4, 20], [11.55, 30], [11.7, 40], [11.85, 50], [12.0, 60], [12.15, 70], [12.3, 80], [12.45, 90], [12.6, 100]]
function batteryPercent(robot: Robot) {
  const voltage = robot.voltage_v
  if (voltage != null && Number.isFinite(voltage)) {
    if (voltage <= batteryCurve[0]![0]) return 0
    if (voltage >= batteryCurve.at(-1)![0]) return 100
    for (let i = 1; i < batteryCurve.length; i++) {
      const [v1, p1] = batteryCurve[i - 1]!
      const [v2, p2] = batteryCurve[i]!
      if (voltage <= v2) return Math.round(p1 + (voltage - v1) * (p2 - p1) / (v2 - v1))
    }
  }
  return robot.battery == null ? null : Math.round(Math.max(0, Math.min(100, robot.battery)))
}
const batteryLabel = (robot: Robot) => {
  if (!connected.value || !robot.online) return '电量未知'
  const percent = batteryPercent(robot)
  return percent == null ? '电量未知' : `3S ${percent}%`
}
const batteryClass = (robot: Robot) => {
  if (!connected.value || !robot.online) return 'unknown'
  const percent = batteryPercent(robot)
  return percent == null ? 'unknown' : percent <= 15 ? 'danger' : percent <= 35 ? 'warn' : 'ok'
}
const batteryVoltageLabel = (robot: Robot) => !connected.value || !robot.online || robot.voltage_v == null ? '—' : `${robot.voltage_v.toFixed(2)} V`
const linkLabel = (robot: Robot) => !connected.value ? '服务器断开' : robot.online ? '车辆在线' : '车辆离线'
const linkClass = (robot: Robot) => !connected.value ? 'unknown' : robot.online ? 'ok' : 'danger'
const poseLabel = (robot: Robot) => !connected.value ? '状态未知' : robot.visible ? '定位有效' : '定位丢失'
const poseClass = (robot: Robot) => !connected.value ? 'unknown' : robot.visible ? 'ok' : 'warn'
const tabLabel = (robot: Robot) => !connected.value ? '未知' : robot.online ? '在线' : '离线'
const tabClass = (robot: Robot) => !connected.value ? 'unknown' : robot.online ? 'ok' : 'danger'

async function api<T>(path: string, body?: unknown, method = 'POST', timeout = 1500): Promise<T> {
  const response = await fetch(path, { method, headers: { 'Content-Type': 'application/json', 'X-Control-ID': controlId }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(timeout) })
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
async function beginHold(direction: string) {
  if (!controlReady.value || active.value) return
  const id = selectedId.value
  const token = ++generation
  active.value = direction
  const send = async () => {
    if (commandPending || token !== generation || !controlReady.value) return
    commandPending = true
    try {
      pendingRequest = api(`/api/robots/${id}/command`, {
        v: joystick.value.y * (selected.value?.effective_max_v ?? 0),
        omega: -joystick.value.x * (selected.value?.effective_max_omega ?? 0),
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
    stopping.value = true
    // Send stop after any in-flight movement request, preserving command order.
    void pendingRequest.catch(() => {}).then(() => action(`/api/robots/${id}/command`, { v: 0, omega: 0, ttl_ms: 100 })).finally(() => stopping.value = false)
  }
}
function moveJoystick(x: number, y: number) {
  joystick.value = { x, y }
  if (!active.value) void beginHold('joystick')
}
async function setMode(mode: 'demo' | 'hardware') {
  if (modePending.value || !connected.value || mode === state.value?.mode) return
  if (!window.confirm(mode === 'hardware' ? '切换到真实设备模式？所有小车将停车并锁定。' : '切换到模拟模式？所有小车将停车并锁定。')) return
  endHold(); modePending.value = true
  try {
    await api('/api/mode', { mode }, 'PUT', 60000)
    state.value = await api<Snapshot>('/api/state', undefined, 'GET')
    toast('模式已切换，全车保持锁定')
  } catch (e) { error.value = (e as Error).message }
  finally { modePending.value = false }
}
async function stopAll() { endHold(); await action('/api/stop') }
function select(id: string) { endHold(); selectedId.value = id }
async function openSettings() {
  endHold()
  try {
    draft.value = await api<Settings>('/api/config', undefined, 'GET')
    addedRobotIndex.value = draft.value.robots.findIndex(r => r.id === selectedId.value)
    settingsSection.value = 'robots'
    originalConfig.value = JSON.stringify(draft.value)
    visionProfile.value = null; originalVision.value = profileJson(null)
    loadedVisionUrl.value = ''
    visionStatus.value = null; visionError.value = ''; cameraDevices.value = []
    configError.value = ''; discardPrompt.value = false; settingsOpen.value = true
    if (draft.value.vision_url) await loadVision()
  }
  catch (e) { error.value = (e as Error).message }
}
async function loadVision() {
  if (!draft.value || visionBusy.value || saving.value) return
  visionBusy.value = true; visionError.value = ''
  const url = draft.value.vision_url || 'http://127.0.0.1:8765'
  try {
    const response = await api<VisionResponse>(`/api/vision/config?url=${encodeURIComponent(url)}`, undefined, 'GET', 5000)
    loadedVisionUrl.value = url
    visionProfile.value = response.config; visionStatus.value = response.state
    originalVision.value = profileJson(response.config)
    draft.value.vision_url = url
  } catch (e) { visionError.value = (e as Error).message }
  finally { visionBusy.value = false }
}
async function pollVision() {
  if (!settingsOpen.value || visionBusy.value || saving.value || visionPollPending || !visionProfile.value || !draft.value?.vision_url) return
  visionPollPending = true
  const url = draft.value.vision_url
  try {
    const response = await api<VisionResponse>(`/api/vision/config?url=${encodeURIComponent(url)}`, undefined, 'GET', 5000)
    if (settingsOpen.value && !visionBusy.value && !saving.value && draft.value?.vision_url === url) {
      visionStatus.value = response.state
      if (visionProfile.value) visionProfile.value.saved_world = response.config.saved_world
    }
  } catch { visionStatus.value = {status: 'error', error: '视觉服务连接中断，请检查服务后重新读取配置'} }
  finally { visionPollPending = false }
}
async function scanCameras() {
  if (dirty.value || visionBusy.value) return
  visionBusy.value = true; visionError.value = ''
  try {
    const result = await api<{cameras: {id: string; name: string}[]}>('/api/vision/cameras', {}, 'POST', 30000)
    cameraDevices.value = result.cameras
    toast(result.cameras.length ? '设备列表已刷新，全车保持锁定' : '未发现相机，可手填 ID；请检查系统相机权限')
  } catch (e) {
    visionNeedsSync.value = true
    visionError.value = `${(e as Error).message}；请重新保存配置以解除安全锁定`
  }
  finally { visionBusy.value = false }
}
async function visionOperation(action: 'calibrate' | 'reset_world' | 'load_world') {
  if (dirty.value || visionBusy.value) return
  visionBusy.value = true; visionError.value = ''
  try {
    await api('/api/vision/operations', { action }, 'POST', 30000)
    toast(action === 'reset_world' ? '标定已清除，全车保持锁定' : '标定已完成并保存，全车保持锁定')
  } catch (e) {
    visionNeedsSync.value = true
    visionError.value = `${(e as Error).message}；请重新保存配置以解除安全锁定`
  }
  finally { visionBusy.value = false; void pollVision() }
}
async function connectCamera(enabled: boolean) {
  if (!visionProfile.value) return
  configError.value = ''
  const form = modalElement.value?.querySelector('form')
  if (form && !form.reportValidity()) return
  if (armedCount.value) {
    await lockForSettings()
    if (configError.value) return
    try { state.value = await api<Snapshot>('/api/state', undefined, 'GET') }
    catch (e) { configError.value = (e as Error).message; return }
  }
  visionProfile.value.enabled = enabled
  await saveSettings(false)
}
async function saveSettings(close = true) {
  if (duplicateTags.value || duplicateIds.value || saving.value || visionBusy.value) return
  configError.value = ''
  saving.value = true
  try {
    const profile = visionProfile.value ? JSON.parse(profileJson(visionProfile.value)) : undefined
    const saved = await api<Settings>('/api/config', { ...draft.value, vision: profile }, 'PUT', 30000)
    draft.value = saved; originalConfig.value = JSON.stringify(saved)
    originalVision.value = profileJson(visionProfile.value)
    visionNeedsSync.value = false
    streamKey.value++; cameraFailed.value = false
    if (close) settingsOpen.value = false
    toast('配置已保存，全车保持锁定')
  } catch (e) { configError.value = (e as Error).message }
  finally { saving.value = false; void pollVision() }
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
watch(() => draft.value?.vision_url, url => {
  if (url !== loadedVisionUrl.value && !saving.value) {
    visionProfile.value = null; visionStatus.value = null
    originalVision.value = profileJson(null); cameraDevices.value = []
  }
})
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
onMounted(() => {
  connect()
  detailObserver = new IntersectionObserver(entries => { detailVisible.value = !!entries[0]?.isIntersecting })
  if (detailPanel.value) detailObserver.observe(detailPanel.value)
  visionTimer = setInterval(pollVision, 1500)
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
  disposed = true; document.body.style.overflow = ''; clearTimeout(noticeTimer); endHold(); clearTimeout(reconnect); clearInterval(clockTimer); clearInterval(visionTimer); socket?.close(); detailObserver?.disconnect()
  window.removeEventListener('pointerup', endHold); window.removeEventListener('pointercancel', endHold)
  window.removeEventListener('blur', endHold); window.removeEventListener('keydown', keydown)
  document.removeEventListener('visibilitychange', pageHidden)
})
</script>

<template>
  <div v-if="mobilePage" class="remote-page">
    <header class="remote-header"><a href="/" class="remote-brand"><img src="/favicon.svg" alt="" />ACField <span>/ 控制台</span></a><span class="connection" :class="{ off: !connected, connected }"><i></i>{{ connected ? '服务器已连接' : '服务器连接中断' }}</span></header>
    <main class="remote-main">
      <div class="remote-title"><div><span class="remote-eyebrow">REMOTE CONTROL</span><h1>小车控制</h1></div><span class="mode-tag">{{ !connected ? '离线' : state?.mode === 'hardware' ? '真实设备' : '模拟环境' }}</span></div>
      <div v-if="error" class="error-banner" role="alert">{{ error }}<button aria-label="关闭提示" @click="error = ''"><X :size="16" /></button></div>
      <div v-if="state?.estop" class="remote-estop"><span>全局停止已锁定</span><button :disabled="!connected" @click="action('/api/reset-stop')">释放全局停止</button></div>
      <label class="remote-select">选择小车<select :value="selectedId" :disabled="!state?.robots.length" @change="select(($event.target as HTMLSelectElement).value)"><option v-for="robot in state?.robots" :key="robot.config.id" :value="robot.config.id">{{ robot.config.name }} · {{ robot.config.id }}</option></select></label>
      <template v-if="selected">
        <div class="remote-status"><span class="status-chip" :class="linkClass(selected)"><Wifi :size="15" />{{ linkLabel(selected) }}</span><span class="status-chip" :class="poseClass(selected)"><Crosshair :size="15" />{{ poseLabel(selected) }}</span><span class="status-chip" :class="batteryClass(selected)" title="按 3S 锂电池 10.5–12.6 V 估算"><Battery :size="16" />{{ batteryLabel(selected) }}</span></div>
        <div class="remote-control-heading"><div><h2>手动控制</h2><p role="status">{{ blockedReason || '控制已就绪' }}</p></div><button class="lock-toggle" :class="{ armed: selected.armed }" :disabled="armPending || (!selected.armed && !canArm) || !connected" @click="toggleArm"><UnlockKeyhole v-if="selected.armed" :size="15"/><LockKeyhole v-else :size="15" />{{ armPending || selected.arm_pending ? '确认中…' : selected.armed ? '锁定控制' : '解锁控制' }}</button></div>
        <TouchJoystick :disabled="!controlReady" :active="active === 'joystick'" :connected="connected" @move="moveJoystick" @stop="endHold" @emergency="endHold(); action(`/api/robots/${selectedId}/command`, { v: 0, omega: 0, ttl_ms: 100 })" />
        <div class="remote-telemetry"><span>X <b>{{ metric(selected.x) }}</b> m</span><span>Y <b>{{ metric(selected.y) }}</b> m</span><span>朝向 <b>{{ deg(selected.theta) }}</b></span></div>
      </template>
      <p v-else class="remote-empty">{{ connected ? '没有可用的小车' : '正在连接服务器…' }}</p>
      <button class="remote-stop-all" :disabled="!connected" @click="stopAll"><Square :size="16" fill="currentColor" />全局停止</button>
    </main>
    <div v-if="notice" class="toast" role="status"><Check :size="17" />{{ notice }}</div>
  </div>
  <div v-else class="shell">
    <aside class="rail">
      <a class="brand-mark" href="/" aria-label="ACField 首页"><img src="/favicon.svg" alt="" /></a>
      <button class="rail-button current" title="实验控制台" aria-label="实验控制台" @click="endHold(); expanded = false; windowTop()"><Grid2X2 :size="21" /></button>
      <button class="rail-button" title="设备与场地设置" aria-label="设备与场地设置" @click="openSettings"><Settings2 :size="21" /></button>
      <div class="rail-bottom"><button class="rail-button" aria-label="操作说明" title="操作说明" @click="help = true"><CircleHelp :size="21" /></button><span class="avatar" title="本地实验工作台">本地</span></div>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <div class="wordmark">ACField<span class="wordmark-dot">/</span></div>
        <span class="header-divider"></span><span class="workspace-name">多智能体实验室</span>
        <div class="top-right"><span class="connection" :class="{ off: !connected, connected }"><i></i>{{ connected ? '服务器已连接' : '服务器连接中断' }}</span><span class="mono header-time">{{ new Date(now).toLocaleTimeString('zh-CN', { hour12: false }) }}</span></div>
      </header>
      <main>
        <section class="page-heading">
          <div><div class="eyebrow">WORKSPACE / LIVE CONTROL</div><h1>实验控制台 <span class="mode-tag">{{ !connected ? '连接未就绪' : state?.mode === 'hardware' ? '真实设备' : '模拟环境' }}</span></h1><p>观测场地，连接设备，让每一次协同清晰可见。</p></div>
          <div class="heading-actions"><a class="button subtle mobile-page-link" href="/mobile"><Smartphone :size="16" />手机控制</a><button class="button subtle" @click="openSettings"><Settings2 :size="16" />实验配置</button><button class="button emergency" :disabled="!connected" @click="stopAll"><Square :size="13" fill="currentColor" />全局停止<span class="keycap">Space</span></button></div>
        </section>
        <div class="mode-bar"><span>运行模式</span><div class="mode-switch" role="group" aria-label="运行模式"><button :class="{ chosen: state?.mode === 'demo' }" :aria-pressed="state?.mode === 'demo'" :disabled="!connected || modePending" @click="setMode('demo')">模拟数据</button><button :class="{ chosen: state?.mode === 'hardware' }" :aria-pressed="state?.mode === 'hardware'" :disabled="!connected || modePending" @click="setMode('hardware')">真实设备</button></div><span class="mode-caption">{{ state?.mode === 'hardware' ? '真实车辆与相机定位' : '模拟车辆与定位' }}</span></div>
        <div v-if="!connected && state" class="error-banner" role="status">连接已中断，以下为最后一次收到的状态。正在自动重连…</div>
        <div v-if="error" class="error-banner" role="alert">{{ error }}<button aria-label="关闭提示" @click="error = ''"><X :size="16" /></button></div>
        <div v-if="state?.estop" class="stop-banner"><LockKeyhole :size="16" /><span>全局停止已锁定。释放后，小车仍需逐车解锁。</span><button :disabled="!connected" @click="action('/api/reset-stop')">释放全局停止 →</button></div>
        <section class="stats-row">
          <div class="stat"><span class="stat-icon green"><Radio :size="19" /></span><div><span class="stat-label">在线设备</span><div class="stat-value mono">{{ online }}<span>/ {{ state?.robots.length ?? 4 }}</span></div></div><span class="stat-note"><i :class="{ gray: !online }"></i>{{ !connected ? '服务器断开' : online ? '链路正常' : '暂无在线车' }}</span></div>
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
            <div class="robot-tabs"><button v-for="(r, i) in state?.robots" :key="r.config.id" :class="{ selected: selectedId === r.config.id }" :aria-pressed="selectedId === r.config.id" :aria-label="`选择设备 ${r.config.name}`" @click="select(r.config.id)"><i :style="{ background: r.config.color }"></i><span>{{ r.config.name }}</span><small :class="`status-text-${tabClass(r)}`">{{ tabLabel(r) }}</small></button></div>
            <template v-if="selected">
              <div class="device-identity"><div class="device-symbol" :style="{ '--robot-color': selected.config.color }"><Focus :size="27" /></div><div><h2>{{ selected.config.name }}</h2><span class="mono">{{ selected.config.id.toUpperCase() }} <span class="muted">/ TAG {{ selected.config.tag_id }}</span></span></div><span class="online-label" :class="linkClass(selected)"><i></i>{{ linkLabel(selected) }}</span></div>
              <div class="device-status"><span class="status-chip" :class="linkClass(selected)"><Wifi :size="13" />{{ linkLabel(selected) }}</span><span class="status-chip" :class="poseClass(selected)"><Crosshair :size="13" />{{ poseLabel(selected) }}</span><span class="status-chip" :class="batteryClass(selected)" title="按 3S 锂电池 10.5–12.6 V 估算"><Battery :size="15" />{{ batteryLabel(selected) }}</span></div>
              <div class="position-summary"><span>X <b class="mono">{{ metric(selected.x, 2) }}</b> m</span><span>Y <b class="mono">{{ metric(selected.y, 2) }}</b> m</span><span><b class="mono">{{ deg(selected.theta) }}</b></span></div>
              <div class="control-heading"><h3>手动控制</h3><button class="lock-toggle" :class="{ armed: selected.armed }" :disabled="armPending || (!selected.armed && !canArm) || !connected" :title="blockedReason" @click="toggleArm"><UnlockKeyhole v-if="selected.armed" :size="12"/><LockKeyhole v-else :size="12" />{{ armPending || selected.arm_pending ? '确认中…' : selected.armed ? '锁定控制' : '解锁控制' }}</button></div>
              <p v-if="blockedReason" class="control-explanation" role="status">{{ blockedReason }}</p><div v-else class="control-explanation ready">控制已就绪</div>
              <TouchJoystick :disabled="!controlReady" :active="active === 'joystick'" :connected="connected" @move="moveJoystick" @stop="endHold" @emergency="endHold(); action(`/api/robots/${selectedId}/command`, { v: 0, omega: 0, ttl_ms: 100 })" />
              <p class="control-hint">{{ selected.armed ? '松开控制即停车' : '解锁后可以控制小车' }}</p>
              <div class="command-state"><span class="command-dot" :class="{ on: selected.armed }"></span><span>{{ !connected ? '连接中断 · 暂停控制' : selected.reason }}</span><span class="mono">#{{ String(selected.seq).padStart(4, '0') }}</span></div><div class="ack-status">{{ commandLabel(selected) }} · 有效期 300 ms</div>
              <details class="telemetry-section"><summary>定位与速度详情<ChevronDown :size="14" /></summary>              <div class="telemetry-grid"><div><label>X 坐标 <span>m</span></label><strong class="mono">{{ metric(selected.x, 3) }}</strong></div><div><label>Y 坐标 <span>m</span></label><strong class="mono">{{ metric(selected.y, 3) }}</strong></div><div><label>车体朝向</label><strong class="mono">{{ deg(selected.theta) }}</strong></div><div><label>距上次定位 <span>ms</span></label><strong class="mono">{{ metric(selected.pose_age_ms, 0) }}</strong></div></div>
              <div class="velocity-row"><span>实测线速度<strong class="mono">{{ metric(selected.measured_v) }}<small> m/s</small></strong></span><span>视觉估计<strong class="mono">{{ metric(selected.estimated_v) }}<small> m/s</small></strong></span></div>
              <div class="extra-telemetry"><span>左 / 右编码计数 <b class="mono">{{ selected.encoder_left ?? '—' }} / {{ selected.encoder_right ?? '—' }}</b></span><span>电池电压 · 3S <b class="mono">{{ batteryVoltageLabel(selected) }}</b></span><span>实测角速度 <b class="mono">{{ metric(selected.measured_omega) }} rad/s</b></span><span>估计加速度 <b class="mono">{{ metric(selected.acceleration) }} m/s²</b></span></div>
</details>
            </template><div v-else class="waiting-device">等待设备状态…</div>
          </aside>
          <section class="panel camera-panel"><div class="panel-header"><div class="panel-title"><Camera :size="16" />视觉观察<span class="small-label">{{ state?.mode === 'demo' ? 'PREVIEW' : 'CAMERA' }}</span></div><button class="text-button" :disabled="!connected || state?.mode !== 'hardware' || !state.camera.available" @click="cameraOpen = !cameraOpen; cameraFailed = false">{{ state?.mode !== 'hardware' ? '模拟模式无相机' : !state.camera.available ? '等待相机连接' : cameraOpen ? '收起画面' : '展开画面' }}<Expand :size="13" /></button></div>
            <div v-if="cameraOpen && state?.mode === 'hardware' && state.camera.available && !cameraFailed" class="camera-stream"><img :src="'/api/camera/stream'" alt="实时相机画面" @error="cameraFailed = true" /></div>
            <div v-else class="camera-placeholder"><div class="camera-illustration"><Camera :size="30" /><span class="camera-corner tl"></span><span class="camera-corner br"></span></div><div><h3>{{ state?.mode === 'demo' ? '先在模拟场地完成一次实验' : '连接你的俯视相机' }}</h3><p>{{ state?.mode === 'demo' ? '当前使用合成定位。接入 AprilTag 视觉服务后，可在此查看实时画面。' : cameraFailed ? '相机流暂时不可用，点击展开画面重试。' : state?.camera.reason }}</p></div><span class="camera-tag">{{ state?.camera.available ? '已连接' : '未接入相机' }}</span></div>
          </section>
          <section class="panel events-panel"><div class="panel-header"><div class="panel-title"><Activity :size="16" />运行记录</div><span class="small-label">本次会话</span></div><div class="events-list"><div v-for="(event, index) in state?.events.slice(0, 4)" :key="`${event.time}-${index}`" class="event"><span class="mono">{{ clock(event.time) }}</span><i></i><span>{{ event.message }}</span></div><div v-if="!state?.events.length" class="empty-events">等待服务器事件</div></div></section>
        </div>
        <footer class="page-footer"><span><Focus :size="12" /> AClab <span class="footer-version">ACField · preview</span></span><span>本地实验工作台 <span>·</span> {{ state?.mode === 'demo' ? '模拟设备，不连接真实电机' : '局域网设备通信' }}</span><span class="mono">HTTP / WS / UDP</span></footer>
      </main>
    </div>
    <div v-if="notice" class="toast" role="status"><Check :size="17" />{{ notice }}</div>
    <button v-if="selected && !settingsOpen && !help && !detailVisible" class="mobile-control-jump" @click="focusControls"><Focus :size="17" />{{ selected.config.name }} · 查看控制</button>
    <div v-if="settingsOpen && draft" class="modal-backdrop settings-backdrop" @click.self="closeSettings">
      <section ref="modalElement" tabindex="-1" class="modal settings-workspace" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <div class="modal-header"><div><h2 id="settings-title">实验配置</h2><p>设备、场地与视觉设置</p></div><button aria-label="关闭配置" @click="closeSettings"><X :size="20" /></button></div>
        <form @submit.prevent="saveSettings()" @invalid.capture="revealInvalid">
          <div class="settings-layout">
            <nav class="settings-nav" aria-label="配置分区">
              <button type="button" :class="{ current: settingsSection === 'robots' }" :aria-current="settingsSection === 'robots' ? 'location' : undefined" @click="showSettingsSection('robots')"><Focus :size="17" />小车<span>{{ draft.robots.length }}</span></button>
              <button type="button" :class="{ current: settingsSection === 'arena' }" :aria-current="settingsSection === 'arena' ? 'location' : undefined" @click="showSettingsSection('arena')"><Maximize2 :size="17" />场地</button>
              <button type="button" :class="{ current: settingsSection === 'camera' }" :aria-current="settingsSection === 'camera' ? 'location' : undefined" @click="showSettingsSection('camera')"><Camera :size="17" />相机与标定</button>
            </nav>
            <div class="modal-body settings-content" @scroll="trackSettingsSection">
              <p class="settings-note">保存配置后全车保持锁定，需要重新释放全局停止并解锁。</p>
              <div v-if="armedCount" class="settings-warning"><span>{{ armedCount }} 辆小车尚未锁定，暂时不能保存。</span><button type="button" class="button subtle" :disabled="!connected" @click="lockForSettings">全车停车并锁定</button></div>
              <p v-if="duplicateIds" class="modal-error" role="alert">设备 ID 不能重复，请为每辆小车分配不同的 ID。</p>
              <p v-if="duplicateTags" class="modal-error" role="alert">AprilTag ID 不能重复，请为每辆小车分配不同的标签。</p>
              <section id="settings-robots" class="settings-group" aria-labelledby="settings-robots-title">
                <div class="settings-section-title robot-section-title"><div><h3 id="settings-robots-title">小车配置 <span>{{ draft.robots.length }} / 16</span></h3><p>管理车辆身份、尺寸和速度限制</p></div><button type="button" class="button subtle" :disabled="draft.robots.length >= 16" @click="addRobot"><Plus :size="15" />添加小车</button></div>
                <details v-for="(robot, index) in draft.robots" :key="index" class="robot-config" :open="index === addedRobotIndex"><summary><i :style="{ background: robot.color }"></i>{{ robot.name }} <span class="mono">{{ robot.id.toUpperCase() }}</span><ChevronDown :size="14" /></summary><div class="form-grid"><label>设备 ID<input v-model="robot.id" pattern="[a-zA-Z0-9_-]{1,32}" maxlength="32" title="1 至 32 位字母、数字、下划线或短横线" required /></label><label>设备名称<input v-model="robot.name" maxlength="40" required /></label><label>AprilTag ID<input v-model.number="robot.tag_id" type="number" min="0" max="586" required /></label><label>标签黑框边长 / m<input v-model.number="robot.tag_size" type="number" min=".005" max="1" step=".001" required /></label><label>标签安装高度 / m<input v-model.number="robot.tag_height" type="number" min="0" max="10" step=".0001" required /></label><label>显示颜色<input v-model="robot.color" type="color" /></label><label>车体长度 / m<input v-model.number="robot.length" type="number" min=".01" max="1" step=".01" required /></label><label>车体宽度 / m<input v-model.number="robot.width" type="number" min=".01" max="1" step=".01" required /></label><label>标签前向偏移 / m<input v-model.number="robot.tag_offset_x" type="number" min="-1" max="1" step=".001" required /></label><label>标签左向偏移 / m<input v-model.number="robot.tag_offset_y" type="number" min="-1" max="1" step=".001" required /></label><label>航向修正 / rad<input v-model.number="robot.heading_offset" type="number" min="-3.142" max="3.142" step=".001" required /></label><label>最大线速度 / m/s<input v-model.number="robot.max_v" type="number" min=".02" max="1" step=".01" required /></label><label>最大角速度 / rad/s<input v-model.number="robot.max_omega" type="number" min=".1" max="6" step=".1" required /></label></div><p class="field-note">真实模式保存时，标签黑框边长与安装高度会同步到视觉服务。航向修正在主控端应用，请按实测填写。设备 ID 必须与车端固件配置一致。</p><button type="button" class="button robot-delete" :disabled="draft.robots.length <= 1" :title="draft.robots.length <= 1 ? '至少保留一辆小车' : '删除这辆小车'" @click="removeRobot(index)"><Trash2 :size="15" />删除小车</button></details>
              </section>
              <section id="settings-arena" class="settings-group" aria-labelledby="settings-arena-title">
                <h3 id="settings-arena-title">场地尺寸</h3><p class="settings-group-description">设置实验场地的实际宽度和高度</p>
                <div class="form-grid"><label>宽度 / m<input v-model.number="draft.arena_width" type="number" min="1" max="20" step=".1" required /></label><label>高度 / m<input v-model.number="draft.arena_height" type="number" min="1" max="20" step=".1" required /></label></div>
              </section>
              <section id="settings-camera" class="settings-group"><CameraSettings :settings="draft" :profile="visionProfile" :status="visionStatus" :cameras="cameraDevices" :busy="visionBusy || saving" :error="visionError" :hardware="state?.mode === 'hardware'" :dirty="dirty" :preview="!!state?.camera.available" :stream-key="streamKey" @refresh="loadVision" @scan="scanCameras" @connect="connectCamera" @operation="visionOperation" /></section>
            </div>
          </div>
          <div v-if="configError" class="modal-error" role="alert">{{ configError }}</div>
          <div v-if="discardPrompt" class="discard-prompt" role="alert"><span>有未保存的修改，是否放弃？</span><button type="button" @click="discardPrompt = false">继续编辑</button><button type="button" @click="settingsOpen = false; discardPrompt = false">放弃修改</button></div>
          <div class="modal-footer"><span class="save-state">{{ saving ? '正在保存…' : dirty ? '有未保存的修改' : '配置未修改' }}</span><button type="button" class="button subtle" @click="closeSettings">取消</button><button type="submit" class="button primary" :disabled="saving || visionBusy || !connected || armedCount > 0 || duplicateTags || duplicateIds || !dirty"><Check :size="16" />{{ saving ? '保存中…' : '保存配置' }}</button></div>
        </form>
      </section>
    </div>
    <div v-if="help" class="modal-backdrop" @click.self="help = false"><section ref="modalElement" tabindex="-1" class="modal help-modal" role="dialog" aria-modal="true" aria-labelledby="help-title"><div class="modal-header"><h2 id="help-title">开始一次实验</h2><button aria-label="关闭操作说明" @click="help = false"><X :size="20" /></button></div><div class="modal-body"><ol><li>确认顶部为模拟环境或预期的真实设备模式。</li><li>在场地或设备标签中选择一辆小车。</li><li>确认通信与定位有效，点击「解锁」。</li><li>拖动摇杆控制移动和转向，松开后停车。电脑可用 Tab 聚焦摇杆并按住方向键操作。</li><li>按空格或点击「全局停止」锁定全部设备。</li></ol><p>真实设备需要实现 UDP 协议和独立的车端超时停车。已加入保守的边界与车间距离停车保护，仍需实测定位误差和停止距离；它不会自动规划绕行。故障或指令超时后需重新解锁。</p><p>在「实验配置」中连接相机、填写内参和固定标签坐标，再执行场地标定。真实模式保存时会同步小车标签尺寸和安装高度。</p></div></section></div>
  </div>
</template>
