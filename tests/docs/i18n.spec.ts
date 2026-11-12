import { expect, test, type Page } from '@playwright/test'
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

function pages(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    if (entry.name.startsWith('.') || entry.name === 'public' || entry.name === 'en' || entry.name === 'privacy_docs') return []
    return entry.isDirectory()
      ? pages(join(directory, entry.name)).map(path => entry.name + '/' + path)
      : entry.name.endsWith('.md') ? [entry.name] : []
  }).sort()
}

async function desktopLanguage(page: Page, target: string) {
  const menu = page.locator('.VPNavBarTranslations')
  await menu.getByRole('button').click()
  await menu.getByRole('link', { name: target, exact: true }).click()
}

async function mobileLanguage(page: Page, target: string) {
  await page.getByRole('button', { name: 'mobile navigation', exact: true }).click()
  const menu = page.locator('.VPNavScreenTranslations')
  await menu.getByRole('button').click()
  await menu.getByRole('link', { name: target, exact: true }).click()
}

test('every Chinese document has an English counterpart with matching section anchors', () => {
  const chinese = pages('docs')
  expect(pages('docs/en')).toEqual(chinese)
  for (const path of chinese) {
    const anchors = (source: string) => [...source.matchAll(/^#{2,6} .*\{#([^}]+)\}$/gm)].map(match => match[1])
    const zh = readFileSync(join('docs', path), 'utf8')
    const en = readFileSync(join('docs/en', path), 'utf8')
    expect(anchors(en), path).toEqual(anchors(zh))
    if (path !== 'index.md') expect(anchors(en).length, path).toBeGreaterThan(0)
  }
})

test('desktop home switches in both directions, including locale-specific home links', async ({ page }) => {
  await page.goto('./')
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN')
  await desktopLanguage(page, 'English')
  await expect(page).toHaveURL(new RegExp('/en/$'))
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page.locator('.VPNavBarMenu').getByRole('link', { name: 'Get started', exact: true })).toHaveAttribute('href', '/acfield/en/guide/quickstart')
  await expect(page.locator('.VPHomeHero').getByRole('link', { name: 'Get started →' })).toHaveAttribute('href', '/acfield/en/guide/quickstart')
  await desktopLanguage(page, '简体中文')
  await expect(page).toHaveURL(new RegExp('/acfield/$'))
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN')
})

for (const [path, anchor] of [
  ['guide/quickstart', 'requirements'], ['guide/python-sdk', 'installation'],
  ['design/philosophy', 'make-the-experiment-path-understandable'],
  ['reference/api', 'endpoints']
]) {
  test('desktop retains topic and section: ' + path, async ({ page }) => {
    await page.goto(path + '#' + anchor)
    await desktopLanguage(page, 'English')
    await expect(page).toHaveURL(new RegExp('/en/' + path + '#' + anchor + '$'))
    await expect(page.locator('[id="' + anchor + '"]')).toBeAttached()
    await expect(page.locator('.VPDocAsideOutline .outline-title')).toHaveText('On this page')
    await expect(page.locator('.VPSidebar')).toContainText('Usage and development')
    await desktopLanguage(page, '简体中文')
    await expect(page).toHaveURL(new RegExp('/acfield/' + path + '#' + anchor + '$'))
    await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN')
  })
}

for (const path of pages('docs/en')) {
  test('English content and navigation stay in English: ' + path, async ({ page }) => {
    const route = path.replace(/index\.md$/, '').replace(/\.md$/, '')
    const response = await page.goto('en/' + route)
    expect(response?.status(), path).toBe(200)
    await expect(page.locator('html')).toHaveAttribute('lang', 'en')
    const links = await page.locator('.VPContent a[href], .VPNavBarMenu a[href], .VPSidebar a[href]')
      .evaluateAll(elements => elements.map(element => element.getAttribute('href') || ''))
    const leaks = links.filter(link => link.startsWith('/acfield/')
      && !link.startsWith('/acfield/en/') && !/\.(png|svg|pdf|glb|stl)$/.test(link))
    expect(leaks, path).toEqual([])
    expect(await page.locator('.VPContent').innerText(), path).not.toMatch(/[一-鿿]/)
  })
}

test('English search returns English pages', async ({ page }) => {
  await page.goto('en/guide/python-sdk')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await page.locator('#localsearch-input').fill('ownership')
  const results = page.locator('.VPLocalSearchBox a[href]')
  await expect(results.first()).toBeVisible()
  for (const href of await results.evaluateAll(elements => elements.map(element => element.getAttribute('href')))) {
    expect(href?.startsWith('/acfield/en/')).toBe(true)
  }
})

test('compact desktop switches languages from the extra navigation menu', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 })
  await page.goto('guide/quickstart#requirements')
  for (const target of ['English', '简体中文']) {
    const menu = page.locator('.VPNavBarExtra')
    await menu.getByRole('button', { name: 'extra navigation', exact: true }).click()
    await menu.getByRole('link', { name: target, exact: true }).click()
    await expect(page.locator('html')).toHaveAttribute('lang', target === 'English' ? 'en' : 'zh-CN')
    await expect(page).toHaveURL(new RegExp('/' + (target === 'English' ? 'en/' : '') + 'guide/quickstart#requirements$'))
  }
})

test('mobile switches both ways and shows translated menus without overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('guide/python-sdk#installation')
  await mobileLanguage(page, 'English')
  await expect(page).toHaveURL(new RegExp('/en/guide/python-sdk#installation$'))
  await expect(page.getByRole('button', { name: 'Menu', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await mobileLanguage(page, '简体中文')
  await expect(page).toHaveURL(new RegExp('/acfield/guide/python-sdk#installation$'))
  await expect(page.getByRole('button', { name: '目录', exact: true })).toBeVisible()
  await page.goto('en/')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await mobileLanguage(page, '简体中文')
  await expect(page).toHaveURL(new RegExp('/acfield/$'))
  await mobileLanguage(page, 'English')
  await expect(page).toHaveURL(new RegExp('/en/$'))
})
