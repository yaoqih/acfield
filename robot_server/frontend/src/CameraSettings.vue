<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Settings, VisionProfile, VisionStatus } from './types'

const props = defineProps<{
  settings: Settings; profile: VisionProfile | null; status: VisionStatus | null;
  cameras: {id: string; name: string}[]; busy: boolean; error: string;
  hardware: boolean; dirty: boolean; preview: boolean; streamKey: number;
}>()
const emit = defineEmits<{
  refresh: []; scan: []; connect: [enabled: boolean];
  operation: [action: 'calibrate' | 'reset_world' | 'load_world'];
}>()
const localError = ref('')
const fixedTags = computed(() => Object.entries(props.profile?.tags ?? {}).filter(([, tag]) => tag.role === 'fixed'))
const hasIntrinsics = computed({
  get: () => props.profile?.camera != null,
  set: enabled => {
    if (!props.profile) return
    props.profile.camera = enabled ? {
      image_width: props.profile.width, image_height: props.profile.height,
      camera_matrix: [[0, 0, 0], [0, 0, 0], [0, 0, 1]], dist_coeffs: [0, 0, 0, 0, 0],
    } : null
  },
})
function renameFixed(oldId: string, event: Event) {
  const input = event.target as HTMLInputElement
  const key = String(Number(input.value))
  if (!props.profile || key === oldId) return
  if (!input.checkValidity() || props.profile.tags[key] || props.settings.robots.some(r => r.tag_id === Number(key))) {
    localError.value = '固定标签 ID 必须唯一，且不能与小车标签重复'
    input.value = oldId
    return
  }
  props.profile.tags[key] = props.profile.tags[oldId]!
  delete props.profile.tags[oldId]
  localError.value = ''
}
function resizeDistortion(event: Event) {
  if (!props.profile?.camera) return
  const count = Number((event.target as HTMLSelectElement).value)
  props.profile.camera.dist_coeffs = Array.from({length: count}, (_, i) => props.profile!.camera!.dist_coeffs[i] ?? 0)
}
function selectCamera(event: Event) {
  if (!props.profile) return
  const source = (event.target as HTMLInputElement).value
  if (source !== props.profile.source) {
    props.profile.source = source
    props.profile.camera = null
    localError.value = ''
  }
}
</script>

<template>
  <section class="vision-settings">
    <div class="settings-section-title"><h3>相机与视觉</h3><span>{{ hardware ? '真实设备' : '模拟模式' }}</span></div>
    <p class="field-note" v-if="!hardware">模拟模式下可配置真实相机，车辆位置仍使用模拟数据。</p>
    <label class="full-field">视觉服务地址<input v-model="settings.vision_url" type="url" placeholder="http://127.0.0.1:8765" :disabled="busy" /></label>
    <div class="vision-actions"><button type="button" class="button subtle" :disabled="busy" @click="emit('refresh')">{{ busy ? '操作中…' : '读取服务配置' }}</button><span class="field-note">留空时可通过读取连接本机 8765 端口。</span></div>
    <p v-if="error || localError" class="modal-error" role="alert">{{ error || localError }}</p>
    <template v-if="profile">
      <fieldset :disabled="busy" class="vision-fields">
        <div class="form-grid">
          <label>相机设备<select :value="profile.source" @change="selectCamera"><option v-if="!cameras.some(c => c.id === profile?.source)" :value="profile.source">相机 {{ profile.source }}</option><option v-for="camera in cameras" :key="camera.id" :value="camera.id">{{ camera.name }}</option></select></label>
          <label>相机 ID（可手动填写）<input :value="profile.source" @input="selectCamera" type="text" inputmode="numeric" pattern="[0-9]|[1-5][0-9]|6[0-3]" required /></label>
          <label>采集宽度 / px<input v-model.number="profile.width" type="number" min="16" max="8192" step="1" required /></label>
          <label>采集高度 / px<input v-model.number="profile.height" type="number" min="16" max="8192" step="1" required /></label>
          <label>请求帧率 / fps<input v-model.number="profile.fps" type="number" min="1" max="120" required /></label>
          <label>检测降采样<select v-model.number="profile.decimate"><option :value="1">1× · 完整分辨率</option><option :value="1.5">1.5×</option><option :value="2">2×</option><option :value="3">3×</option><option :value="4">4×</option></select></label>
        </div>
        <p class="field-note">设备列表来自视觉服务所在电脑。刷新扫描 ID 0–5，其他设备可手填；驱动可能调整分辨率或帧率，以下方实际状态为准。小车定位使用 tag36h11。</p>
        <div class="vision-actions"><button type="button" class="button subtle" @click="emit('scan')" :disabled="dirty">刷新设备</button><button type="button" class="button primary" @click="emit('connect', true)">{{ profile.enabled ? '保存并重新连接' : '保存并连接相机' }}</button><button type="button" class="button subtle" @click="emit('connect', false)">保存并断开</button></div>
        <p v-if="dirty" class="field-note">有未保存修改；连接按钮会同时保存全部实验配置。刷新设备和标定前请先保存。</p>

        <details class="vision-details"><summary>相机内参与畸变参数</summary>
          <p class="field-note">填写该相机实测标定结果。更换相机后请重新标定内参；没有内参时仍可预览与识别，但不能输出场地坐标。</p>
          <label class="checkbox-field"><input v-model="hasIntrinsics" type="checkbox" />使用已测量的相机内参</label>
          <div v-if="profile.camera" class="form-grid">
            <label>标定图像宽度<input v-model.number="profile.camera.image_width" type="number" min="16" max="16384" required /></label>
            <label>标定图像高度<input v-model.number="profile.camera.image_height" type="number" min="16" max="16384" required /></label>
            <label>fx / px<input v-model.number="profile.camera.camera_matrix[0][0]" type="number" min=".001" step="any" required /></label>
            <label>fy / px<input v-model.number="profile.camera.camera_matrix[1][1]" type="number" min=".001" step="any" required /></label>
            <label>cx / px<input v-model.number="profile.camera.camera_matrix[0][2]" type="number" step="any" required /></label>
            <label>cy / px<input v-model.number="profile.camera.camera_matrix[1][2]" type="number" step="any" required /></label>
            <label>畸变参数数量<select :value="profile.camera.dist_coeffs.length" @change="resizeDistortion"><option v-for="count in [4,5,8,12,14]" :key="count" :value="count">{{ count }}</option></select></label>
            <label v-for="(_, i) in profile.camera.dist_coeffs" :key="i">{{ ['k1','k2','p1','p2','k3','k4','k5','k6','s1','s2','s3','s4','τx','τy'][i] }}<input v-model.number="profile.camera.dist_coeffs[i]" type="number" step="any" required /></label>
          </div>
        </details>

        <details class="vision-details"><summary>固定标签与场地标定</summary>
          <p class="field-note">坐标单位为米，原点与控制台场地一致，固定标签中心位于地面 z=0。边长填写黑色外框尺寸。修改场地尺寸后，请核对这些实测坐标。</p>
          <div class="fixed-tags"><div class="fixed-tag-row fixed-tag-heading"><span>标签 ID</span><span>黑框边长 / m</span><span>X / m</span><span>Y / m</span></div>
            <div v-for="([id, tag]) in fixedTags" :key="id" class="fixed-tag-row"><input :value="id" @change="renameFixed(id, $event)" type="number" min="0" max="586" :aria-label="`固定标签 ${id} ID`" required /><input v-model.number="tag.size_m" type="number" min=".005" max="1" step=".001" :aria-label="`固定标签 ${id} 边长`" required /><template v-if="tag.world_xyz_m"><input v-model.number="tag.world_xyz_m[0]" type="number" step="any" :aria-label="`固定标签 ${id} X`" required /><input v-model.number="tag.world_xyz_m[1]" type="number" step="any" :aria-label="`固定标签 ${id} Y`" required /></template></div>
          </div>
          <label class="checkbox-field"><input v-model="profile.world.configured" type="checkbox" />已确认固定标签的实测坐标</label>
          <div class="vision-actions"><button type="button" class="button primary" :disabled="dirty || !profile.enabled || !profile.camera || !profile.world.configured" @click="emit('operation', 'calibrate')">标定并保存</button><button type="button" class="button subtle" :disabled="dirty || !profile.enabled || !profile.saved_world" @click="emit('operation', 'load_world')">核验并加载标定</button><button type="button" class="button subtle" :disabled="dirty" @click="emit('operation', 'reset_world')">清除标定</button></div>
          <p class="field-note">需同时看见全部已配置的固定标签。加载时会用当前图像核验相机位置；更换相机或移动后应重新标定。</p>
        </details>
      </fieldset>
      <div v-if="status" class="vision-status" aria-live="polite"><strong>{{ status.status === 'running' ? '视觉服务运行中' : '等待有效图像' }}</strong><span>{{ status.width ?? '—' }} × {{ status.height ?? '—' }} px · {{ status.fps?.toFixed(1) ?? '—' }} fps · 延迟 {{ status.frame_age_ms?.toFixed(0) ?? '—' }} ms</span><span>内参{{ status.calibrated ? '有效' : '未配置或不匹配' }} · 场地{{ status.world_calibrated ? '已标定' : '未标定' }}<template v-if="status.world_info"> · RMS {{ status.world_info.rms_px.toFixed(2) }} px</template></span><span v-if="status.error">{{ status.error }}</span><span v-for="warning in status.warnings ?? []" :key="warning">{{ warning }}</span></div>
      <div v-if="status?.source_kind === 'camera' && status.status === 'running' && settings.vision_url && !dirty" class="vision-preview"><img :key="streamKey" :src="`/api/camera/stream?v=${streamKey}`" alt="配置相机实时预览" /></div>
    </template>
  </section>
</template>
