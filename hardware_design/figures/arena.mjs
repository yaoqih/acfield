/** Editable, bilingual vector drawing. Dimensions describe the requested arena,
 * not a structural drawing or a measured camera footprint. */
import { writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
const output = resolve(dirname(fileURLToPath(import.meta.url)), '../../docs/public/images')
const green = '#307861', ink = '#263e37', muted = '#70847a', blue = '#4c7b9c'
const p = (x, y, z = 0) => [520 + 130 * (x - y), 462 + 65 * (x + y) - 108 * z]
const pts = coordinates => coordinates.map(v => v.join(',')).join(' ')
const esc = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;')
const text = (x, y, value, cls = 'detail', extra = '') => `<text x="${x}" y="${y}" class="${cls}" ${extra}>${esc(value)}</text>`
const line = (a, b, color = muted, width = 1.5, more = '') => `<path d="M${a}L${b}" fill="none" stroke="${color}" stroke-width="${width}" ${more}/>`
const polygon = (points, fill, more = '') => `<polygon points="${pts(points)}" fill="${fill}" ${more}/>`
function cube(x, y, z, w, d, h, colors) {
  return polygon([p(x,y,z),p(x+w,y,z),p(x+w,y,z+h),p(x,y,z+h)],colors[1]) +
    polygon([p(x+w,y,z),p(x+w,y+d,z),p(x+w,y+d,z+h),p(x+w,y,z+h)],colors[2]) +
    polygon([p(x,y,z+h),p(x+w,y,z+h),p(x+w,y+d,z+h),p(x,y+d,z+h)],colors[0])
}
function tag(x, y, id) {
  return polygon([p(x-.11,y-.11,.008),p(x+.11,y-.11,.008),p(x+.11,y+.11,.008),p(x-.11,y+.11,.008)],'#fff') +
    polygon([p(x-.075,y-.075,.01),p(x+.075,y-.075,.01),p(x+.075,y+.075,.01),p(x-.075,y+.075,.01)],'#3b5047') +
    text(...p(x,y,.04).map((v,i)=>v+(i?5:0)),String(id),'tag-id','text-anchor="middle"')
}
function robot(x, y, color, id) {
  let body = cube(x-.12,y-.12,.02,.24,.24,.09,[color,'#294f43','#1f4036'])
  body += cube(x-.065,y-.07,.115,.13,.14,.006,['#f9faf5','#e5e8df','#d7dfd3'])
  const [cx,cy] = p(x,y,.13)
  body += `<circle cx="${cx}" cy="${cy}" r="4" fill="${ink}"/>`
  body += text(cx+17,cy-13,id,'detail')
  return body
}
function laptop(x,y) {
  return `<g transform="translate(${x} ${y})"><path d="M-42 0V-58Q-42-63-37-63H37Q42-63 42-58V0" fill="#52665e"/><rect x="-35" y="-56" width="70" height="47" rx="2" fill="#eaf2e9"/><path d="M-31-42H-13M-31-33H8M-31-24H22" stroke="#719b81" stroke-width="2"/><path d="M-42 0H42L56 15H-56Z" fill="#b7c3b9"/><path d="M-9 5H9L12 11H-12Z" fill="#87988c"/></g>`
}
function router(x,y) {
  return `<g transform="translate(${x} ${y})"><path d="M-27-8L-35-42M27-8L35-42" stroke="#65776b" stroke-width="5" stroke-linecap="round"/><rect x="-42" y="-11" width="84" height="26" rx="6" fill="#d1dbce" stroke="#889c8b"/><circle cx="-25" cy="2" r="2.5" fill="${green}"/><circle cx="-14" cy="2" r="2.5" fill="${green}"/><path d="M-17-51Q0-66 17-51M-10-43Q0-52 10-43" fill="none" stroke="${green}" stroke-width="2"/></g>`
}
for (const en of [false, true]) {
  const t = (zh, english) => en ? english : zh
  const title = t('3 × 3 m · 多小车实验场地','3 × 3 m · multi-robot arena')
  let body = text(54,50,'ACFIELD / SHARED EXPERIMENT INFRASTRUCTURE','eyebrow') +
    text(54,103,title,'title') + text(54,142,t('一侧立杆 · 直角横臂 · 中央俯拍 · 本地网络','Side mast · right-angle boom · central overhead view · local network'),'sub')
  body += `<rect x="40" y="188" width="1025" height="862" rx="18" fill="#f1f5ef"/>` +
    text(68,228,t('01 / 空间布置','01 / SPATIAL LAYOUT'),'eyebrow')
  // Floor with a metric 0.5 m grid, thick active-boundary outline.
  body += polygon([p(0,0,-.045),p(3,0,-.045),p(3,3,-.045),p(0,3,-.045)],'#d6e0d2')
  body += polygon([p(0,0),p(3,0),p(3,3),p(0,3)],'#e6eee2','stroke="#658f76" stroke-width="2"')
  for(let i=.5;i<3;i+=.5) body += line(p(i,0),p(i,3),'#c7d8c2',1) + line(p(0,i),p(3,i),'#c7d8c2',1)
  body += polygon([p(.23,.23,.003),p(2.77,.23,.003),p(2.77,2.77,.003),p(.23,2.77,.003)],'none','stroke="#95b49a" stroke-dasharray="5 7"')
  for (const [x,y,id] of [[.16,.16,0],[2.84,.16,1],[2.84,2.84,2],[.16,2.84,3]]) body += tag(x,y,id)
  // Field-of-view edges indicate intent only; actual coverage follows lens/FOV.
  const camera = p(1.5,1.5,2.47)
  for(const corner of [[0,0],[3,0],[3,3],[0,3]]) body += line(camera,p(...corner),'#9cbba0',1.2,'stroke-dasharray="4 7"')
  body += line(camera,p(1.5,1.5),'#79a18a',1.3,'stroke-dasharray="4 5"') + `<ellipse cx="520" cy="657" rx="12" ry="6" fill="none" stroke="#6a9d80"/>`
  for(const data of [[.83,.9,'#43816a','car-01'],[2.1,.72,'#6289a0','car-02'],[1.03,2.15,'#ad9255','car-03'],[2.2,2.08,'#a17c85','car-04']]) body += robot(...data)
  // Mast outside active floor; horizontal boom runs perpendicular to it.
  body += cube(-.35,1.33,0,.34,.34,.07,['#8b9e8e','#667c6d','#536c5d'])
  const foot=p(-.18,1.5,.07), elbow=p(-.18,1.5,2.65), tip=p(1.5,1.5,2.65)
  body += line(foot,elbow,'#61786c',14,'stroke-linecap="square"') + line(elbow,tip,'#61786c',14,'stroke-linecap="square"')
  body += line([foot[0]-3,foot[1]],[elbow[0]-3,elbow[1]],'#9eb3a3',3) + line([elbow[0],elbow[1]-3],[tip[0],tip[1]-3],'#9eb3a3',3)
  body += line(p(-.18,1.5,2.1),p(.28,1.5,2.65),'#799386',5)
  body += line(tip,camera,'#61786c',5) + cube(1.38,1.39,2.41,.24,.22,.1,['#84978c','#425d50','#536c5f'])
  body += `<ellipse cx="${camera[0]}" cy="${camera[1]+8}" rx="10" ry="5" fill="#233c35"/><ellipse cx="${camera[0]}" cy="${camera[1]+8}" rx="5" ry="2.5" fill="#83a2ac"/>`
  // Camera cable is tied along the boom/mast, terminating outside the floor.
  body += `<path d="M${camera}L${tip[0]} ${tip[1]-10}L${elbow[0]-12} ${elbow[1]-10}V${foot[1]+15}L85 650V746H107" fill="none" stroke="${blue}" stroke-width="3"/>`
  body += laptop(107,746) + router(266,901)
  body += `<path d="M163 755H196V902H221" fill="none" stroke="#64756c" stroke-width="3"/>`
  body += `<path d="M308 900Q401 861 468 821" fill="none" stroke="${green}" stroke-width="2" stroke-dasharray="6 6" marker-end="url(#wireless)"/>`
  // Labels placed in the open space above the scene.
  body += text(76,300,t('场外立杆','External mast'),'label') + text(76,326,t('固定底座 / 防晃','Anchored base')) + line([215,309],p(-.18,1.5,1.8),'#96a99b',1.2)
  body += text(448,265,t('直角横臂','Right-angle boom'),'label') + text(448,292,t('伸向场地中央','Reaches arena centre')) + line([470,305],p(.8,1.5,2.65),'#96a99b',1.2)
  body += text(650,344,t('摄像头 · 垂直俯拍','Camera · vertical view'),'label') + text(650,371,t('光轴投影 (1.5, 1.5) m','Optical axis at (1.5, 1.5) m')) + line([635,359],camera,'#96a99b',1.2)
  body += text(657,408,t('H：由镜头视场与标定确定','H: choose from lens FOV and calibration'))
  body += text(63,792,t('Server 电脑','Server computer'),'label') + text(63,817,t('视觉 + 控制服务','Vision + control service'))
  body += text(207,951,t('路由器 / AP','Router / AP'),'label')
  body += text(356,922,t('Wi-Fi / UDP','Wi-Fi / UDP'))
  // Two orthogonal 3 m dimensions in the floor plane.
  for(const [a,b,c,d] of [[p(0,3),p(3,3),p(0,3.35),p(3,3.35)],[p(3,0),p(3,3),p(3.35,0),p(3.35,3)]]) {
    body += line(a,c,'#9db09e',1) + line(b,d,'#9db09e',1) + line(c,d,'#6e8c76',1.3,'marker-start="url(#dimension)" marker-end="url(#dimension)"')
    const x=(c[0]+d[0])/2,y=(c[1]+d[1])/2
    body += `<rect x="${x-32}" y="${y-16}" width="64" height="28" rx="8" fill="#f1f5ef"/>` + text(x,y+5,'3.0 m','dim','text-anchor="middle"')
  }
  body += text(68,1015,t('空间示意；小车图标放大，支架高度未定。','Schematic; robots enlarged and support height unspecified.'))
  // Top view, metrically proportioned square with a centre-point dimension.
  body += `<rect x="1095" y="188" width="465" height="405" rx="18" fill="#f1f5ef"/>` + text(1123,228,t('02 / 平面尺寸','02 / PLAN DIMENSIONS'),'eyebrow')
  body += `<rect x="1210" y="265" width="258" height="258" fill="#e4eddf" stroke="#638b70" stroke-width="2"/>`
  for(let i=1;i<6;i++)body += line([1210+i*43,265],[1210+i*43,523],'#c7d8c2',1) + line([1210,265+i*43],[1468,265+i*43],'#c7d8c2',1)
  body += `<rect x="1186" y="386" width="16" height="16" rx="2" fill="#61786c"/><path d="M1194 394H1339" stroke="#61786c" stroke-width="7"/><circle cx="1339" cy="394" r="8" fill="${blue}"/><path d="M1339 271V517" stroke="#85a98c" stroke-dasharray="4 5"/>`
  body += line([1210,544],[1468,544],'#6e8c76',1.3,'marker-start="url(#dimension)" marker-end="url(#dimension)"') + text(1339,570,'3.0 m','dim','text-anchor="middle"')
  body += text(1199,354,t('≥1.5 m + 退让','≥1.5 m + setback')) + text(1352,426,t('中心','Centre'))
  // Connection topology emphasizes wired camera, wired PC and wireless robots.
  body += `<rect x="1095" y="613" width="465" height="437" rx="18" fill="#f1f5ef"/>` + text(1123,653,t('03 / 连接关系','03 / CONNECTIONS'),'eyebrow')
  const nodes=[
    [680,t('俯拍摄像头','Overhead camera'),t('图像流','Image stream')],
    [785,t('Server 电脑','Server computer'),t('AprilTag 定位 + robot_server','AprilTag vision + robot_server')],
    [890,t('路由器 / AP','Router / AP'),t('实验局域网','Experiment LAN')],
    [990,t('小车 × 4','4 × robots'),'ESP32 · car-01…04']
  ]
  for(const [y,title,detail]of nodes)body += `<rect x="1140" y="${y}" width="374" height="57" rx="9" fill="#fff" stroke="#d5e0d2"/>` + text(1160,y+24,title,'node-title') + text(1160,y+45,detail,'small')
  for(const[y,label,color,dash]of[[737,t('USB / 有线图像连接','USB / wired video'),blue,false],[842,'Ethernet / LAN','#64756c',false],[947,'Wi-Fi · UDP ↕',green,true]]) {
    body += `<path d="M1174 ${y}v48" fill="none" stroke="${color}" stroke-width="2" ${dash?'stroke-dasharray="4 4"':''}/>` + text(1193,y+29,label,'small')
  }
  body += `<path d="M54 1080H1546" stroke="#d2dfd0"/>` + text(54,1114,t('场地边界 3 × 3 m；地面标签位置、相机视场和横臂刚度需在搭建后实测。','3 × 3 m active boundary; measure tag positions, camera coverage and boom stiffness after installation.'),'note')
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1150" viewBox="0 0 1600 1150" role="img" aria-labelledby="title desc"><title id="title">${esc(title)}</title><desc id="desc">${esc(t('侧边立杆与直角横臂支撑中央俯拍摄像头。摄像头有线连接 Server 电脑，电脑通过网线连接路由器，小车通过 Wi-Fi 与路由器通信。','An external side mast and right-angle boom hold a downward camera above the centre. The camera is wired to the server computer; the computer connects to a router by Ethernet, and robots connect by Wi-Fi.'))}</desc><defs><marker id="dimension" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M10 0L0 5L10 10" fill="#6e8c76"/></marker><marker id="wireless" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10" fill="${green}"/></marker></defs><style>text{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;fill:${ink}}.eyebrow{font-size:13px;font-weight:650;letter-spacing:1.4px;fill:#477d65}.title{font-size:38px;font-weight:650;letter-spacing:-.7px}.sub{font-size:18px;fill:#61786a}.label{font-size:18px;font-weight:650}.detail{font-size:14px;fill:#627b6b}.dim{font-size:17px;font-weight:600}.tag-id{font-size:9px;font-weight:700;fill:#fff}.note{font-size:16px;fill:#627b6b}.node-title{font-size:17px;font-weight:600}.small{font-size:13px;fill:#627b6b}</style><rect width="1600" height="1150" rx="20" fill="#fbfcf9"/>${body}</svg>`
  await writeFile(resolve(output,'arena'+(en?'-en':'')+'.svg'),svg)
}
console.log('Wrote bilingual arena diagrams.')
