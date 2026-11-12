<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { Robot, Snapshot } from './types'
import { ServerClock } from './timeSync'

type Sample = { time: number; left: number; right: number; segment: number }
const state = ref<Snapshot | null>(null)
const connected = ref(false)
const selectedId = ref('car-01')
const selected = computed(() => state.value?.robots.find(r => r.config.id === selectedId.value))
const controlId = globalThis.crypto?.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
const error = ref('')
const samples = ref<Sample[]>([])
const speed = ref(0.05)
const pwm = ref(18)
const diagnostic = computed(() => selected.value?.encoder_diagnostic)
const speedLimit = computed(() => Math.min(0.1, selected.value?.effective_max_v ?? 0))
const commandedPwm = computed(() => diagnostic.value ? Math.round((selected.value?.target_v ?? 0) * diagnostic.value.pwm_per_mps) : null)
const running = ref(false)
const releasing = ref(false)
const now = ref(performance.now())
let socket: WebSocket | null = null
let reconnect: ReturnType<typeof setTimeout> | undefined
let timer: ReturnType<typeof setInterval> | undefined
let syncTimer: ReturnType<typeof setInterval> | undefined
let runTimer: ReturnType<typeof setInterval> | undefined
let clock = new ServerClock()
let probe = -1
let lastUpdate = 0
let lastAck = 0
let seq = 0
let segment = 0
let broken = true
let disposed = false
let runDirection = 1
let activeVelocity = 0
let runDiagnostic = false
let started = 0

const blocked = computed(() => {
  const r = selected.value
  if (!connected.value) return '服务器连接中断'
  if (state.value?.system_fault) return `控制服务故障：${state.value.system_fault}`
  if (state.value?.estop) return '全局停止已锁定，请先在控制台释放'
  if (!r) return '请选择小车'
  if (r.fault) return `设备故障：${r.fault}`
  if (!r.online) return '车辆离线'
  if (!r.bound) return '等待停车绑定确认'
  if (!r.visible && !state.value?.allow_unlocalized_control) return '定位不可用'
  if (r.control_owner && r.control_owner !== controlId) return '另一页面正在控制此车'
  if (releasing.value) return '正在停车'
  if (r.firmware?.includes('encoder-diagnostic') && !diagnostic.value) return '主控尚未识别此诊断固件，请更新配套主控'
  return ''
})
const count = (n: number | null | undefined) => n == null ? '—' : n.toLocaleString('zh-CN')
function wheelSpeed(n: number | null | undefined) {
  const fresh = connected.value && selected.value?.online && (selected.value.heartbeat_age_ms ?? Infinity) <= 500
  return fresh && n != null && Number.isFinite(n) ? n.toFixed(3) : '—'
}
const lastSample = computed(() => samples.value.at(-1))
function delta(side: 'left' | 'right') {
  const last = lastSample.value
  if (!last || broken || !connected.value || now.value - last.time > 500) return '—'
  const earlier = samples.value.find(s => s.segment === last.segment && s.time >= last.time - 1000)
  if (!earlier || last.time - earlier.time < 500) return '—'
  return `${last[side] - earlier[side] > 0 ? '+' : ''}${last[side] - earlier[side]}`
}
const chart = computed(() => {
  const list = samples.value
  if (!list.length) return { left: '', right: '', min: 0, max: 0 }
  const end = now.value
  const bases = new Map<number, Sample>()
  for (const sample of list) if (!bases.has(sample.segment)) bases.set(sample.segment, sample)
  const values = list.flatMap(s => [s.left - bases.get(s.segment)!.left, s.right - bases.get(s.segment)!.right])
  let min = Math.min(0, ...values), max = Math.max(0, ...values)
  if (min === max) { min--; max++ }
  const pad = (max-min)*.08; min -= pad; max += pad
  function path(side: 'left' | 'right') {
    let prev = -1
    return list.map(s => {
      const x = 45 + Math.max(0, Math.min(1, (s.time - (end - 10000)) / 10000)) * 925
      const value = s[side] - bases.get(s.segment)![side]
      const y = 230 - (value - min) / (max-min) * 200
      const result = `${s.segment === prev ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`
      prev = s.segment
      return result
    }).join(' ')
  }
  return { left: path('left'), right: path('right'), min: Math.round(min), max: Math.round(max) }
})
function record(r: Robot | undefined) {
  const time = performance.now()
  if (!r?.online || (r.heartbeat_age_ms != null && r.heartbeat_age_ms > 500) || r.encoder_left == null || r.encoder_right == null || !Number.isFinite(r.encoder_left) || !Number.isFinite(r.encoder_right)) { broken = true; return }
  const last = samples.value.at(-1)
  if (broken || !last || time - last.time > 500) { segment++; broken = false }
  samples.value = [...samples.value.filter(s => time - s.time <= 10000), { time, left: r.encoder_left, right: r.encoder_right, segment }].slice(-500)
}
function clearChart() { samples.value = []; broken = true }
async function release(id: string, reason: string, keepalive = false) {
  if (!id) return
  try {
    const response = await fetch(`/api/robots/${encodeURIComponent(id)}/release`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Control-ID': controlId }, body: JSON.stringify({ reason: reason.slice(0, 120) }), keepalive })
    if (!response.ok) throw new Error('停车请求失败')
  } catch { if (!keepalive) error.value = '停车请求失败；请检查连接，运动指令会在有效期结束后过期。' }
}
function stop(reason = '用户点击停车', keepalive = false) {
  clearInterval(runTimer); runTimer = undefined
  running.value = false
  if (socket && (socket.bufferedAmount > 4096 || reason === '控制确认超时')) socket.close()
  if (keepalive) { void release(selectedId.value, reason, true); return }
  if (releasing.value) return
  releasing.value = true
  void release(selectedId.value, reason).finally(() => { releasing.value = false })
}
function send(v: number) {
  if (!socket || socket.readyState !== WebSocket.OPEN || socket.bufferedAmount > 4096) throw new Error('控制通道拥塞或已断开')
  // Allow brief radio interruptions while keeping the existing device watchdog.
  const command: { v: number; omega: number; ttl_ms: number; immediate?: boolean; hold?: boolean } = { v, omega: 0, ttl_ms: 500 }
  if (diagnostic.value) {
    // The known diagnostic firmware accepts unscheduled commands with its normal TTL.
    command.immediate = true
    command.hold = true
  }
  socket.send(JSON.stringify({ type: 'control', owner: controlId, seq: ++seq, robot_id: selectedId.value, command }))
}
function inputVelocity(): number | null {
  if (diagnostic.value) {
    const value = Number(pwm.value), max = diagnostic.value.max_pwm
    if (!Number.isInteger(value) || value < 0 || value > max) { error.value = `PWM 必须是 0–${max} 的整数，尚未应用此输入`; return null }
    return value / diagnostic.value.pwm_per_mps
  }
  const value = Number(speed.value)
  if (!Number.isFinite(value) || value <= 0 || value > speedLimit.value) { error.value = `目标速度必须大于 0 且不超过 ${speedLimit.value.toFixed(3)} m/s，尚未应用此输入`; return null }
  return value
}
function applyOutput() {
  const velocity = inputVelocity()
  if (velocity == null) return
  activeVelocity = velocity * runDirection
  error.value = ''
  if (running.value && runDiagnostic) {
    try { send(activeVelocity) } catch (e) { error.value = (e as Error).message; stop(error.value) }
  }
}
function start(direction: number) {
  if (blocked.value || running.value) return
  const velocity = inputVelocity()
  if (velocity == null) return
  runDirection = direction; activeVelocity = velocity * direction; runDiagnostic = !!diagnostic.value
  running.value = true; error.value = ''; lastAck = performance.now()
  started = performance.now()
  if (runDiagnostic) {
    // The server maintains the device TTL while this control connection is open.
    // Browser background timer throttling must not interrupt diagnostic motion.
    try { send(activeVelocity) } catch (e) { error.value = (e as Error).message; stop(error.value) }
    return
  }
  const tick = () => {
    now.value = performance.now()
    if (blocked.value || now.value - lastUpdate > 1500) { error.value = blocked.value || '状态更新超时'; stop(error.value); return }
    if (runDiagnostic !== !!diagnostic.value) { error.value = '车辆控制模式已变化'; stop(error.value); return }
    if (now.value - started >= 120000) { error.value = '已达到 120 秒运行上限'; stop('达到 120 秒运行上限'); return }
    try {
      if (now.value - lastAck > 250) throw new Error('控制确认超时')
      send(activeVelocity)
    } catch (e) { error.value = (e as Error).message; stop(error.value) }
  }
  tick()
  if (running.value) runTimer = setInterval(tick, 25)
}
function selectRobot(event: Event) {
  const next = (event.target as HTMLSelectElement).value
  if (next === selectedId.value) return
  stop('切换小车'); selectedId.value = next; clearChart()
}
function connect() {
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
  socket = ws
  ws.onopen = () => {
    clock = new ServerClock()
    const sync = () => { if (ws.readyState === WebSocket.OPEN && ws.bufferedAmount < 4096) { probe = performance.now(); ws.send(JSON.stringify({ type: 'time_sync', t1: probe })) } }
    sync(); clearInterval(syncTimer); syncTimer = setInterval(sync, 1000)
  }
  ws.onmessage = event => {
    const message = JSON.parse(event.data)
    if (message.type === 'time_sync') { if (message.t1 === probe) clock.observe(message.t1, message.t2, message.t3, performance.now()); return }
    if (message.type === 'control_ack') { lastAck = performance.now(); return }
    if (message.type === 'control_error') { error.value = message.message; stop(error.value); return }
    state.value = message; lastUpdate = performance.now(); connected.value = true
    if (!message.robots.some((r: Robot) => r.config.id === selectedId.value)) { stop('车辆已从配置移除'); selectedId.value = message.robots[0]?.config.id ?? ''; clearChart() }
    record(selected.value)
    if (running.value && (blocked.value || runDiagnostic !== !!diagnostic.value)) { error.value = blocked.value || '车辆控制模式已变化'; stop(error.value) }
  }
  ws.onclose = () => { connected.value = false; broken = true; clearInterval(syncTimer); stop('控制连接断开'); if (!disposed) reconnect = setTimeout(connect, 1500) }
  ws.onerror = () => ws.close()
}
function pageExit() { stop('页面已离开', true) }
onMounted(() => {
  connect()
  timer = setInterval(() => {
    now.value = performance.now()
    if (!diagnostic.value && connected.value && now.value - lastUpdate > 1500) { connected.value = false; broken = true; stop('状态更新超时'); socket?.close() }
    samples.value = samples.value.filter(s => now.value - s.time <= 10000)
  }, 100)
  window.addEventListener('pagehide', pageExit)
})
onUnmounted(() => {
  disposed = true; stop('页面已关闭', true); clearTimeout(reconnect); clearInterval(timer); clearInterval(syncTimer); socket?.close()
  window.removeEventListener('pagehide', pageExit)
})
</script>

<template>
  <div class="diagnostics">
    <header><a href="/">← 返回控制台</a><span :class="connected ? 'online' : 'offline'">{{ connected ? '● 服务器已连接' : '● 服务器连接中断' }}</span></header>
    <main>
      <div class="intro"><p class="eyebrow">HARDWARE DIAGNOSTICS</p><h1>编码器排查</h1><p>转动双轮，观察编码计数，轻晃线材和插头，查找变化异常的一侧。</p></div>
      <div class="notice"><strong>请先将小车架空，确保双轮离地。</strong> 单次最多运行 2 分钟；诊断固件支持切到后台继续运行。点击停车、离开页面或控制连接断开时停车。</div>
      <div v-if="state?.mode === 'hardware' && selected?.online" class="notice" role="status"><template v-if="diagnostic"><strong>编码器诊断固件已启用。</strong> 电机按 PWM 占空比运行，编码器无响应和方向保护已关闭；指令到达即执行，无需等待校时。PWM 不代表 m/s。排查完成后请烧录普通固件。</template><template v-else-if="selected.firmware?.includes('encoder-diagnostic')"><strong>诊断固件尚未被主控识别。</strong> 请更新配套主控后再运行。</template><template v-else><strong>当前是普通固件。</strong> 0.2.8 正式固件采用开环控制，编码器仅用于观测。需要直接设置 PWM 时，可烧录编码器诊断固件。</template></div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <section class="panel controls">
        <div class="panel-title"><div><h2>电机控制</h2><p>{{ state?.mode === 'hardware' ? '真实设备' : '模拟环境' }} · 双轮直行</p></div><span :class="selected?.online && connected ? 'online' : 'offline'">{{ selected?.online && connected ? '车辆在线' : '车辆离线' }}</span></div>
        <div class="fields"><label>选择小车<select :value="selectedId" @change="selectRobot"><option v-for="robot in state?.robots" :key="robot.config.id" :value="robot.config.id">{{ robot.config.name }} · {{ robot.config.id }}</option></select></label><label v-if="diagnostic">PWM（0–{{ diagnostic.max_pwm }} / 255）<input v-model.number="pwm" type="number" min="0" :max="diagnostic.max_pwm" step="1" /></label><label v-else>目标速度（m/s）<input v-model.number="speed" type="number" min="0.001" :max="speedLimit" step="0.001" /></label></div>
        <p v-if="diagnostic && diagnostic.max_pwm === 35" class="small">当前车端仍是上限 35 的旧诊断固件。烧录 0.2.4-encoder-diagnostic 后可使用完整 PWM 0–255。</p>
        <p v-if="diagnostic" class="small" data-testid="commanded-pwm">主控指令 PWM：{{ commandedPwm }} / 255（{{ (Math.abs(commandedPwm ?? 0) / 255 * 100).toFixed(1) }}%）；上限 {{ diagnostic.max_pwm }} / 255。调整后点击「应用输出」，运行中也可生效。</p>
        <p v-else class="small">本页目标速度上限 {{ speedLimit.toFixed(3) }} m/s。调整后点击「应用输出」，运行中也可生效。</p>
        <p class="status" role="status">{{ blocked || (running ? '电机运行中' : '控制已就绪') }}<template v-if="selected?.stop_reason"> · 车端状态：{{ selected.stop_reason }}</template></p>
        <p v-if="selected?.last_stop_reason && !selected.armed" class="status">最近停车原因：{{ selected.last_stop_reason }}</p>
        <p v-if="running && selected?.diagnostic_remaining_ms != null" class="small">本次剩余 {{ Math.ceil(selected.diagnostic_remaining_ms / 1000) }} 秒</p>
        <p v-if="selected?.warning" class="status">设备警告：{{ selected.warning }}</p>
        <p v-if="selected?.motion_echo_rejections != null" class="small">车端因遥测回显过期拒收运动指令：{{ selected.motion_echo_rejections }} 次（本次开机累计）。持续增加表示通信延迟仍超过车端窗口。</p>
        <div class="buttons"><button :disabled="!!blocked || running" @click="start(1)">开始前进</button><button :disabled="!!blocked || running" @click="start(-1)">开始后退</button><button class="secondary" :disabled="!!blocked || !running" @click="applyOutput">应用输出</button><button class="stop" :disabled="!connected || releasing" @click="stop()">停车</button></div>
        <div class="metrics"><div>左轮编码器估算速度<strong data-testid="speed-left">{{ wheelSpeed(selected?.wheel_left) }} <small>m/s</small></strong></div><div>右轮编码器估算速度<strong data-testid="speed-right">{{ wheelSpeed(selected?.wheel_right) }} <small>m/s</small></strong></div></div>
        <p class="small">测速依赖编码器、每圈脉冲数和轮径标定；线材接触不良时读数可能失真，不能据此确认真实车速。需要重新运行时，直接点击开始按钮。</p>
      </section>
      <section class="panel chart-panel">
        <div class="panel-title"><div><h2>编码器变化</h2><p>最近 10 秒 · 相对窗口内每段起点的累计脉冲</p></div><button class="secondary" @click="clearChart">清空曲线</button></div>
        <div class="metrics"><div><span class="dot left"></span>左编码器 <strong data-testid="encoder-left">{{ count(connected && selected?.online ? selected.encoder_left : null) }}</strong><small>近约 1 秒变化 {{ delta('left') }}</small></div><div><span class="dot right"></span>右编码器 <strong data-testid="encoder-right">{{ count(connected && selected?.online ? selected.encoder_right : null) }}</strong><small>近约 1 秒变化 {{ delta('right') }}</small></div></div>
        <div class="graph"><svg viewBox="0 0 1000 260" role="img" aria-label="左右编码器最近十秒相对计数曲线" preserveAspectRatio="none"><line x1="45" y1="30" x2="970" y2="30"/><line x1="45" y1="130" x2="970" y2="130"/><line x1="45" y1="230" x2="970" y2="230"/><text x="0" y="34">{{ chart.max }}</text><text x="0" y="234">{{ chart.min }}</text><path data-testid="line-left" class="line-left" :d="chart.left"/><path data-testid="line-right" class="line-right" :d="chart.right"/></svg><div class="axis"><span>10 秒前</span><span>现在</span></div></div>
        <p v-if="state?.mode === 'demo' && selected?.encoder_left == null" class="small">模拟模式不产生编码器计数；连接真实设备后显示。</p>
        <p class="small">数值为车端原始累计计数，未应用方向修正，两侧正负可能不同。曲线来自遥测采样，并非每个脉冲的波形；离线或数据中断后重新起算。计数停滞或突变可作为排查线索，不能单独判定故障。</p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.diagnostics{min-height:100vh;background:#f4f7f6;color:#1c302d;font-family:inherit}.diagnostics header{height:64px;display:flex;align-items:center;justify-content:space-between;padding:0 max(24px,calc((100vw - 1100px)/2));background:white;border-bottom:1px solid #dce7e3;font-size:14px}.diagnostics a{color:#237a69;text-decoration:none;font-weight:700}.online{color:#24856e}.offline{color:#b55349}.diagnostics main{max-width:1100px;margin:auto;padding:36px 24px 70px}.intro h1{font-size:32px;margin:8px 0}.intro p,.panel-title p{color:#71837d;margin:5px 0}.eyebrow{font-size:11px;letter-spacing:.14em;font-weight:800;color:#2b8874!important}.notice,.error{padding:16px 20px;border-radius:10px;margin:24px 0;background:#fff6dd;color:#765a1e;line-height:1.6}.error{background:#fff0ee;color:#aa4036}.panel{background:#fff;border:1px solid #e0ebe7;border-radius:14px;padding:24px;margin-top:18px;box-shadow:0 3px 16px #24483c08}.panel-title{display:flex;justify-content:space-between;align-items:center;gap:16px}.panel h2{font-size:19px;margin:0}.panel-title p,.small{font-size:13px}.fields{display:flex;gap:16px;margin-top:22px}.fields label{display:flex;flex-direction:column;gap:7px;font-size:13px;font-weight:700;color:#586f67;flex:1}.fields select,.fields input{height:42px;border:1px solid #d8e5e0;border-radius:8px;padding:0 12px;background:white;color:#203b33}.status{font-size:14px;color:#61766e;margin:20px 0}.buttons{display:flex;flex-wrap:wrap;gap:10px}.diagnostics button{border:0;border-radius:8px;background:#287c69;color:white;font-weight:700;padding:11px 18px;cursor:pointer}.diagnostics button:disabled{opacity:.45;cursor:not-allowed}.diagnostics button.secondary{background:#edf4f1;color:#286b5b}.diagnostics button.stop{background:#ba5048}.small{color:#7b8c86;line-height:1.7;margin:16px 0 0}.metrics{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:22px 0}.metrics>div{background:#f6f9f8;border-radius:10px;padding:16px;color:#5d746b;font-size:13px}.metrics strong{display:block;color:#223d34;font-size:25px;margin:8px 0;font-variant-numeric:tabular-nums}.metrics small{color:#83948e}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}.left{background:#278c73}.right{background:#e29349}.graph{width:100%;overflow:hidden}.graph svg{width:100%;height:250px;overflow:visible}.graph line{stroke:#e6efeb;stroke-width:1}.graph text{font-size:12px;fill:#8b9d96}.graph path{fill:none;stroke-width:2.5;vector-effect:non-scaling-stroke}.line-left{stroke:#278c73}.line-right{stroke:#e29349}.axis{display:flex;justify-content:space-between;padding-left:4.5%;color:#92a39c;font-size:12px}@media(max-width:600px){.diagnostics main{padding:24px 14px 50px}.diagnostics header{padding:0 16px}.panel{padding:18px}.intro h1{font-size:27px}.fields{flex-direction:column}.metrics{gap:8px}.metrics>div{padding:12px}.metrics strong{font-size:20px}.buttons button{flex:1 1 42%}.graph svg{height:190px}}
</style>
