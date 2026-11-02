# Documentation and deployment

The site uses VitePress. Source lives in `docs/` and is reviewed with code. GitHub Pages hosts static documentation, not the control service.

## Local preview {#local-preview}

```bash
npm ci
npm run docs:dev
# Build and preview production output
npm run docs:build
npm run docs:preview
```

Build output is `docs/.vitepress/dist/` and is not committed. The site supports local search, light/dark themes, mobile navigation and edit links.

## Languages and navigation {#languages-and-navigation}

Chinese pages live directly under `docs/`; English counterparts use identical relative paths under `docs/en/`. For example, `guide/python-sdk.md` pairs with `en/guide/python-sdk.md`. Both languages have a complete homepage and documentation tree.

VitePress `locales` configures language-aware navigation, sidebars, search and interface labels. Use the language menu to switch to the same topic. On mobile, open the navigation menu to find language options. Links within an English page should remain within the English tree.

When adding or changing a page, maintain both versions and keep corresponding section anchors aligned. Shared navigation paths live in `docs/.vitepress/config.mts`. Verify both directions of language switching rather than adding an ordinary link to the English homepage.

Run the browser regression checks before submitting:

```bash
npx playwright install chromium
npm run docs:build
npm run docs:test
```

Checks cover matching pages and section anchors, language switching in both directions, English navigation and search, and mobile menus. Tests start a production preview automatically; set `DOCS_TEST_URL` to check a deployed site.

## GitHub Actions {#github-actions}

`.github/workflows/docs.yml` builds and runs browser regression checks on main pushes, pull requests and manual runs. Pull requests validate only; main/manual runs deploy after successful checks using native Pages artifacts and short-lived identity tokens, without a personal access token.

Initially select **Settings → Pages → Build and deployment → Source → GitHub Actions**. Maintainers can also create a Pages site with `build_type=workflow` through the GitHub API. Later main commits publish automatically.

The site is **https://yaoqih.github.io/acfield/**, with English at **https://yaoqih.github.io/acfield/en/**. The project base is `/acfield/` in `docs/.vitepress/config.mts`. Repository/organization/domain changes must update the base, sitemap, favicon and citation URLs together.

## Editing content {#editing-content}

Guides explain tasks; design pages explain rationale, costs and reconsideration conditions; reference pages describe exact interfaces; the status page distinguishes implementation, software checks and physical evidence.

Builds check Markdown links. Homepage/layout changes also need desktop/mobile checks for readability, assets and navigation. Add new pages to the sidebar and do not describe planned capabilities as delivered.
