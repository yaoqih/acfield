// Z-up, millimetres. Printed parts come directly from the audited assembly GLB.
// Purchased-part details are illustrative, constrained by nominal envelopes.
import * as T from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const scene = new T.Scene()
scene.background = new T.Color('#f4f6f3')
const renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
renderer.setPixelRatio(1)
renderer.shadowMap.enabled = true
renderer.shadowMap.type = T.PCFSoftShadowMap
renderer.outputColorSpace = T.SRGBColorSpace
renderer.toneMapping = T.ACESFilmicToneMapping
renderer.toneMappingExposure = 1.35
document.body.appendChild(renderer.domElement)
const camera = new T.OrthographicCamera()
camera.up.set(0, 0, 1)
scene.add(new T.HemisphereLight(0xffffff, 0x65746a, 2.6))
const light = new T.DirectionalLight(0xfff7e7, 4.1)
light.position.set(-120, -160, 400)
light.castShadow = true
light.shadow.mapSize.set(2048, 2048)
Object.assign(light.shadow.camera, { left: -260, right: 260, top: 340, bottom: -260, near: 1, far: 900 })
light.shadow.bias = -0.08
light.shadow.normalBias = 0.2
light.shadow.radius = 4
scene.add(light)
const fill = new T.DirectionalLight(0xdceefa, 1.5)
fill.position.set(150, 180, 140)
scene.add(fill)
const root = new T.Group()
scene.add(root)
const gltf = await new GLTFLoader().loadAsync('/hardware_design/print_v11/assembly.glb')
const params = await (await fetch('/hardware_design/print_v11/parameters.json')).json()
const materials = {}
function material(color, metalness = 0, roughness = 0.55) {
  const key = color + metalness + roughness
  return materials[key] ||= new T.MeshStandardMaterial({ color, metalness, roughness })
}
const palette = { chassis: '#276c61', top: '#e8e7d9', nylon: '#dfdcd0', tyre: '#263033', metal: '#a2aeb4', brass: '#b29558', pcb: '#18453b', cell: '#b56b32' }
function mesh(geometry, color, parent, position, metalness = 0, roughness = 0.55) {
  const m = new T.Mesh(geometry, material(color, metalness, roughness))
  m.position.set(...position)
  m.castShadow = true; m.receiveShadow = true
  parent.add(m)
  return m
}
function box(size, at, color, parent, metalness = 0) { return mesh(new T.BoxGeometry(...size), color, parent, at, metalness) }
function cylinder(radius, length, at, color, parent, axis = 'z', metalness = 0) {
  const m = mesh(new T.CylinderGeometry(radius, radius, length, 64), color, parent, at, metalness)
  if (axis === 'z') m.rotation.x = Math.PI / 2
  return m
}
function tube(points, color, radius, parent) {
  const curve = new T.CatmullRomCurve3(points.map(p => new T.Vector3(...p)))
  return mesh(new T.TubeGeometry(curve, 40, radius, 8, false), color, parent, [0, 0, 0])
}
function original(name, parent, color, metalness = 0) {
  const object = gltf.scene.getObjectByName(name)
  if (!object) throw new Error('Missing CAD component: ' + name)
  const m = object.clone()
  m.traverse(child => { if (child.isMesh) {
    // The exported GLB contains positions and indices, but no normals. Generate
    // face normals before using a lit material, keeping CAD edges crisp.
    child.geometry = child.geometry.toNonIndexed()
    child.geometry.computeVertexNormals()
    child.material = material(color, metalness); child.castShadow = true; child.receiveShadow = true
  } })
  parent.add(m)
}
function group(name) { const g = new T.Group(); g.name = name; root.add(g); return g }
const chassis = group('chassis')
original('chassis', chassis, palette.chassis)
const top = group('top')
original('top_board', top, palette.top)
// Real tag36h11 ID10 from the repository; the complete margin is 112.5 mm.
const tag = await new T.TextureLoader().loadAsync('/output/apriltags_90mm/tag36h11_id010_robot.png')
tag.colorSpace = T.SRGBColorSpace; tag.magFilter = T.NearestFilter; tag.minFilter = T.NearestFilter
const tagMesh = new T.Mesh(new T.PlaneGeometry(params.tag_outer_white_mm, params.tag_outer_white_mm), new T.MeshStandardMaterial({ map: tag, roughness: 0.9, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 }))
tagMesh.position.z = params.tag_z_mm + 0.08; top.add(tagMesh)
const posts = group('posts')
for (const object of gltf.scene.children) {
  if (/^(top|board)_nylon/.test(object.name)) original(object.name, posts, palette.nylon)
}
const battery = group('battery')
original('battery', battery, palette.cell)
box([10, 31.12, 24.12], [-14, 0, 21.5], '#323d40', battery) // retention strap illustration
box([24, 20, 0.15], [-14, 0, 33.65], '#ece5c9', battery)
tube([[22.5, -8, 27], [30, -8, 29], [33, -4, 33], [30, 2, 36]], '#a14436', 0.7, battery)
tube([[22.5, -6, 27], [29, -6, 30], [31, -2, 34], [30, 4, 36]], '#33393b', 0.7, battery)
box([6, 7, 4], [30, 3, 36], '#c49b39', battery)
const board = group('board')
const [bx, by] = params.board_outline_envelope_center_xy_mm
box([...params.board_outline_envelope_xy_mm, params.board_thickness_ASSUMED_mm], [bx, by, params.board_bottom_z_mm + 0.8], palette.pcb, board)
// Connector blocks, radio shield and headers are visual keys, not vendor CAD.
box([18, 21, 3], [bx + 12, by + 12, 40.1], '#a9afb3', board, 0.7)
box([13, 9, 1.8], [bx + 12, by + 27, 40], '#202526', board)
box([9, 9, 4], [bx - 3, by - 14, 40.6], '#3f4847', board)
for (const x of [-16, -3, 10]) {
  for (const y of [-23, -5]) {
    box([9, 7, 5], [bx + x, by + y, 41.1], '#ece4cf', board)
    box([6, 3.4, 0.3], [bx + x, by + y, 43.8], '#766a52', board)
  }
}
for (const x of [19, 24]) for (let i = 0; i < 12; i++) {
  box([2.5, 2.5, 3], [bx + x, by - 23 + i * 3.4, 40.3], '#292e2d', board)
  cylinder(0.45, 2, [bx + x, by - 23 + i * 3.4, 42.5], '#bfa159', board, 'z', 0.6)
}
for (const y of [-12, 8]) box([8, 7, 3], [bx - 29, by + y, 40.5], '#b5bbbd', board, 0.7)
for (const x of [-5, 53]) for (const y of [-24.5, 24.5]) {
  cylinder(2.8, 0.7, [x, y, 39], '#d3c697', board)
  cylinder(1.5, 0.8, [x, y, 39.4], '#384941', board)
}
const drives = []
for (const side of [-1, 1]) {
  const motor = group('motor' + side); const wheel = group('wheel' + side)
  original('original_bracket_' + side + '_ASSUMED', motor, palette.nylon)
  original('shaft_' + side, motor, palette.metal, 0.65)
  const y = side * params.motor_center_abs_y_mm, x = params.axle_x_mm
  box([12.2, 10, 10.5], [x, y + side * 10.5, 17], palette.brass, motor, 0.5)
  cylinder(5.8, 16, [x, y - side * 2.5, 17], palette.metal, motor, 'y', 0.6)
  box([12, 4, 10], [x, y - side * 12.5, 17], '#293b38', motor)
  for (const xx of [-4, 4]) cylinder(1.2, 4, [x + xx, y - side * 16, 17], '#d9c383', motor, 'y', 0.6)
  original('wheel_' + side, wheel, palette.tyre)
  cylinder(6, 7.1, [x, side * params.wheel_track_mm / 2, 17], '#b4b9ae', wheel, 'y')
  cylinder(2.1, 7.3, [x, side * params.wheel_track_mm / 2, 17], '#535b57', wheel, 'y', 0.6)
  drives.push({ side, motor, wheel })
}
const caster = group('caster')
for (const object of gltf.scene.children) {
  if (object.name.startsWith('caster_')) original(object.name, caster, object.name.includes('nut') ? palette.nylon : palette.metal, 0.35)
}
original('support_ball', caster, '#d9d8c5')
const ground = mesh(new T.PlaneGeometry(1800, 1800), '#f4f6f3', scene, [0, 0, -0.25])
ground.castShadow = false
let guides
function line(points) {
  const geometry = new T.BufferGeometry().setFromPoints(points.map(p => new T.Vector3(...p)))
  const m = new T.Line(geometry, new T.LineDashedMaterial({ color: 0xaab7ae, dashSize: 3, gapSize: 3, transparent: true, opacity: 0.7 }))
  m.computeLineDistances(); guides.add(m)
}
window.renderFigure = async ({ mode, width, height }) => {
  for (const g of root.children) { g.visible = true; g.position.set(0, 0, 0); g.rotation.set(0, 0, 0) }
  if (guides) { root.remove(guides); guides = undefined }
  const exploded = mode === 'exploded'
  light.castShadow = !exploded
  if (exploded) {
    top.position.z = 150
    board.position.set(22, 0, 83)
    battery.position.set(-34, 0, 44)
    posts.position.z = 14
    // Turn the separated caster over to expose its otherwise hidden ball.
    caster.rotation.y = Math.PI
    caster.position.set(2 * params.caster_x_mm + 38, 0, -46 + 12)
    for (const { side, motor, wheel } of drives) { motor.position.set(0, side * 40, 16); wheel.position.set(0, side * 58, 16) }
    guides = new T.Group(); root.add(guides)
    for (const x of [-60.5, 60.5]) for (const y of [-60.5, 60.5]) line([[x,y,17],[x,y,213]])
    line([[params.caster_x_mm,0,6],[params.caster_x_mm+38,0,-40]])
  } else if (mode === 'open') { top.visible = false }
  else if (mode === 'chassis') { for (const g of root.children) g.visible = g === chassis }
  ground.position.z = exploded ? -57 : -0.25
  const span = exploded ? 328 : 205
  const target = new T.Vector3(exploded ? 0 : 0, 0, exploded ? 83 : 27)
  const direction = new T.Vector3(1.35, -1.7, exploded ? 1.05 : 1.55).normalize()
  camera.position.copy(target).addScaledVector(direction, 600)
  camera.lookAt(target)
  const aspect = width / height
  camera.left = -span * aspect / 2; camera.right = span * aspect / 2
  camera.top = span / 2; camera.bottom = -span / 2
  camera.near = 1; camera.far = 2000; camera.updateProjectionMatrix()
  renderer.setSize(width, height)
  renderer.render(scene, camera)
  function project(point, g) {
    const p = g.localToWorld(new T.Vector3(...point)).project(camera)
    return [(p.x + 1) * width / 2, (1 - p.y) * height / 2]
  }
  return { anchors: { top: project([0,-25,64.6],top), board: project([bx,by,43],board), battery: project([-14,0,33.5],battery), posts: project([60.5,60.5,47],posts), chassis: project([55,-42,12],chassis), motor: project([-16,-36,21],drives[0].motor), wheel: project([-16,-61,20],drives[0].wheel), caster: project([44.8,0,6],caster) }, renderer: renderer.info.render }
}
window.figureReady = true
