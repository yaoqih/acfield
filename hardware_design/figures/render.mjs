/** Reproducible depth-buffered CAD figures. No network assets are loaded. */
import { createServer } from 'node:http'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { resolve, extname, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '@playwright/test'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const out = join(root, 'docs/public/images')
const cache = join(root, 'hardware_design/figures/.cache')
await import('./arena.mjs')
await mkdir(cache, { recursive: true })
await writeFile(join(out, 'robot-tag.png'), await readFile(join(root, 'output/apriltags_104mm/tag36h11_id010_robot.png')))
const types = { '.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.glb': 'model/gltf-binary' }
const server = createServer(async (req, res) => {
  try {
    const path = resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://localhost').pathname))
    if (!path.startsWith(root + '/')) { res.writeHead(403); res.end(); return }
    res.setHeader('Content-Type', types[extname(path)] || 'application/octet-stream')
    res.end(await readFile(path))
  } catch { res.writeHead(404); res.end() }
})
await new Promise(done => server.listen(0, '127.0.0.1', done))
const origin = 'http://127.0.0.1:' + server.address().port
let browser
const esc = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;')
function svg(width, height, title, body) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title"><title id="title">${esc(title)}</title><style>text{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;fill:#263c36}.eyebrow{font-size:13px;font-weight:650;letter-spacing:2px;fill:#447c69}.heading{font-size:34px;font-weight:650;letter-spacing:-1px}.label{font-size:20px;font-weight:600}.detail{font-size:14px;fill:#63766d}.note{font-size:15px;fill:#63766d}</style><rect width="100%" height="100%" rx="20" fill="#f4f6f3"/>${body}</svg>`
}
function text(x, y, value, cls = 'detail') { return `<text x="${x}" y="${y}" class="${cls}">${esc(value)}</text>` }
try {
  browser = await chromium.launch({ headless: true, ...(process.env.DOCS_CHROME_PATH ? { executablePath: process.env.DOCS_CHROME_PATH } : {}), args: ['--enable-webgl', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
  const page = await browser.newPage({ viewport: { width: 1000, height: 1100 }, deviceScaleFactor: 1 })
  page.on('pageerror', error => console.error(error))
  await page.goto(origin + '/hardware_design/figures/scene.html')
  await page.waitForFunction(() => window.figureReady, undefined, { timeout: 30000 })
  const frames = {}
  for (const [mode, width, height] of [['assembled', 1000, 820], ['open', 1000, 820], ['exploded', 1000, 1100], ['chassis', 1000, 820]]) {
    await page.setViewportSize({ width, height })
    const info = await page.evaluate(options => window.renderFigure(options), { mode, width, height })
    const path = join(cache, mode + '.png')
    await page.locator('canvas').screenshot({ path })
    frames[mode] = { ...info, image: 'data:image/png;base64,' + (await readFile(path)).toString('base64') }
    console.log(mode, JSON.stringify(info))
  }
  await writeFile(join(out, 'assembly.png'), await readFile(join(cache, 'assembled.png')))
  await writeFile(join(root, 'hardware_design/print_v11/chassis_preview.png'), await readFile(join(cache, 'chassis.png')))
  const i = (mode, x, y, w, h) => `<image href="${frames[mode].image}" x="${x}" y="${y}" width="${w}" height="${h}"/>`
  for (const en of [false, true]) {
    const suffix = en ? '-en' : ''
    const title = en ? 'V11 · complete assembly' : 'V11 · 完整装配'
    const assembly = svg(1600, 920, title,
      text(52, 48, 'ACFIELD / REFERENCE ROBOT', 'eyebrow') + text(52, 100, title, 'heading') +
      i('assembled', 5, 116, 790, 648) + i('open', 805, 116, 790, 648) +
      text(75, 778, en ? '01  /  Assembled · opaque tag cover' : '01  /  完整装配 · 不透明标签顶盖', 'label') +
      text(875, 778, en ? '02  /  Cover removed · internals visible' : '02  /  移除顶盖 · 查看内部部件', 'label') +
      text(75, 811, en ? '130 × 130 mm cover · 34 mm wheels · 64.6 mm tag height' : '130 × 130 mm 顶盖 · 34 mm 轮 · 标签面高 64.6 mm') +
      text(875, 811, en ? 'Controller, battery, two motors and ball caster included' : '含主控板、电池、双电机与辅助球轮') +
      '<path d="M52 846H1548" stroke="#d5ded5"/>' +
      text(52, 882, en ? 'Printed parts: CAD geometry. Purchased parts: simplified nominal appearance; not a photograph.' : '打印件使用 CAD 几何；采购件为名义尺寸的简化外观示意，非实物照片。', 'note'))
    await writeFile(join(out, 'assembly' + suffix + '.svg'), assembly)
    const title2 = en ? 'V11 · exploded assembly' : 'V11 · 分层爆炸图'
    let body = text(52, 48, 'ACFIELD / COMPONENT GUIDE', 'eyebrow') + text(52, 100, title2, 'heading') +
      text(52, 136, en ? 'Components are separated for clarity. Assembly dimensions are preserved within each part.' : '沿安装方向分离部件，展示层级关系；爆炸间距不代表实际装配尺寸。', 'note') + i('exploded', 300, 145, 1000, 1100)
    const labels = [
      ['top', 1, 65, 246, en ? 'Tag cover' : '标签顶盖', '130 × 130 mm · PETG', true],
      ['board', 2, 1275, 474, en ? 'Main controller' : '主控板', 'ESP32 + TB6612', false],
      ['posts', 3, 1275, 660, en ? 'Mounting posts' : '安装支柱', en ? '4 × 50 mm + 4 × 25 mm' : '50 mm × 4 + 25 mm × 4', false],
      ['battery', 4, 65, 710, en ? '3S battery' : '3S 电池', '73 × 31 × 24 mm', true],
      ['motor', 5, 65, 895, en ? 'Two encoder motors' : '双编码器电机', 'A12 · 12 V · 1:150', true],
      ['wheel', 6, 65, 1075, en ? 'Two drive wheels' : '双驱动轮', en ? 'Ø34 mm · track 122 mm' : '直径 34 mm · 轮距 122 mm', true],
      ['chassis', 7, 1275, 824, en ? 'Printed chassis' : '打印底盘', '130 × 130 mm · PETG', false],
      ['caster', 8, 1275, 1110, en ? 'Auxiliary ball caster' : '辅助球轮', en ? 'CY12B · inverted to show ball' : 'CY12B · 翻转展示球面', false]
    ]
    for (const [key, number, x, y, title, detail, left] of labels) {
      const [ax, ay] = frames.exploded.anchors[key].map((v, index) => v + (index ? 145 : 300))
      const start = left ? x + 215 : x - 20, elbow = left ? 332 : 1250
      body += `<path d="M${start} ${y + 8}H${elbow}L${ax} ${ay}" fill="none" stroke="#99aca1" stroke-width="1.3"/><circle cx="${ax}" cy="${ay}" r="4" fill="#347b65"/><circle cx="${x}" cy="${y - 22}" r="15" fill="#276c5b"/><text x="${x}" y="${y - 17}" text-anchor="middle" style="font-size:14px;fill:#fff">${number}</text>`
      body += text(x, y + 20, title, 'label') + text(x, y + 47, detail)
    }
    body += '<path d="M52 1250H1548" stroke="#d5ded5"/>' + text(52, 1286, en ? 'Purchased parts and PCB details are illustrative. Fasteners are omitted selectively for readability.' : '采购件及板上元件为外观示意；为便于阅读，部分紧固件省略。', 'note')
    await writeFile(join(out, 'exploded' + suffix + '.svg'), svg(1600, 1325, title2, body))
  }
  // Export standalone PNGs as well as scalable originals.
  for (const [name, height] of [['assembly', 920], ['exploded', 1325], ['arena', 1150]]) {
    for (const suffix of ['', '-en']) {
      await page.setViewportSize({ width: 1600, height })
      await page.goto(origin + '/docs/public/images/' + name + suffix + '.svg')
      await page.screenshot({ path: join(out, name + (name === 'assembly' && !suffix ? '-zh' : suffix) + '.png') })
    }
  }
  await writeFile(join(root, 'hardware_design/print_v11/assembly_preview.png'), await readFile(join(out, 'assembly-en.png')))
  console.log('Wrote assembly.png, bilingual assembly/exploded SVGs and hardware previews.')
} finally {
  if (browser) await browser.close()
  await new Promise(done => server.close(done))
}
