# Reaper115 Design System

> iOS 26 / Liquid Glass • Telegram 管理控制台

Reaper115 is a self-hosted Telegram bot + web management console for the **115 网盘 (115 cloud drive)** ecosystem. It crawls 涩花 (sehuatang.net) on a schedule, files matches into 115 offline-download tasks, retries failures, and exposes the whole pipeline through a translucent, "Liquid Glass" Vite + React admin UI in Simplified Chinese.

This design system captures the visual language: brand assets, color, type, glass surfaces, controls, iconography, and component recreations of the web admin and the Telegram bot conversation surface.

---

## Sources

| Source | Path / link |
| --- | --- |
| Codebase | `github.com/yelc66/Reaper115` (private — branch `main`) |
| Brand delivery package | `Reaper115/design-delivery/` (imported into `assets/`) |
| Style guide PDF | originally `design-delivery/StyleGuide.pdf` (not imported — failed binary copy; please re-attach) |
| Web UI | `Reaper115/web-ui/` — Vite + React 18 + TS + Tailwind + Lucide |
| Web UI tokens | `web-ui/src/styles.css` — HSL tokens via CSS vars |
| Web UI components | `web-ui/src/components/ui.tsx` (Button, Card, Badge, Input, …) |
| Mobile / Telegram notes | `design-delivery/Mobile/README.md` |
| Website notes | `design-delivery/Website/README.md` |

Do not assume the reader has access to the private repo — everything used here has been copied into this project.

---

## Index — what's in this folder

```
README.md                  ← you are here
SKILL.md                   ← agent skill manifest (Claude Code-compatible)
colors_and_type.css        ← core CSS variables: color, type, radii, shadow, glass

assets/
  logo/                    ← Reaper115 master SVG + PNG exports (128 / 256 / 1024)
  favicon/                 ← favicon-16, -32, -180
  icons/                   ← function_size.svg|png — upload, download, share_link,
                              cloud_115_file, telegram, settings, security, help

fonts/                     ← (none bundled — uses system SF Pro Display + Inter)

preview/                   ← Design System tab cards (700×N) — colors, type,
                              spacing, components, brand
ui_kits/
  web/                     ← Vite/React admin recreation (Dashboard, Sehua data,
                              Strategy, Tasks, Crawl, Login)
  telegram/                ← Telegram chat surface recreation (intro card,
                              command shortcuts, notification with cover image)
```

No slide template was provided, so `slides/` is intentionally absent.

---

## Brand at a glance

- **Product name:** Reaper115
- **Tagline:** Telegram 管理控制台 (*Telegram management console*)
- **Style line:** "iOS 26 / Liquid Glass" — translucent panels, soft blue depth, compact operational UI
- **Primary surface language:** Simplified Chinese (`zh-CN`)
- **Logo motif:** rounded-square iOS app icon — a cloud bearing the "115" mark, an upload arrow inside a tray below it, and a small Telegram paper-plane badge top-right; soft blue-on-mist background

The logo is *the* brand: it doubles as Telegram bot avatar, favicon, sidebar mark, and login glyph. Never crop the rounded-square, never recolor it.

---

## CONTENT FUNDAMENTALS — voice & copy

The product is built by and for a Chinese-speaking power-user. Copy is **terse, technical, second-person-implicit, and operational** — closer to a piece of infrastructure than a consumer product.

### Voice rules

| Rule | Example (good) | Example (avoid) |
| --- | --- | --- |
| Imperative or noun-first labels, no honorifics | `开始爬取`, `批量离线`, `重试` | ~~`您可以点击此处开始爬取吗？`~~ |
| Short hint copy, ≤ 22 chars when possible | `24h 格式，每日定时爬取前一天数据` | long marketing-ish sentences |
| Mix Chinese + technical English / numerals | `115 OpenAPI`, `Token 文件`, `SSE` | translating these into Chinese |
| Use bot/dev terminology directly | `重试队列`, `离线任务`, `SSE 实时日志` | softened consumer phrasing |
| Status as 2-character labels | `空闲` / `运行中` / `已离线` / `待处理` / `异常` | `Currently idle`, `Now running` |
| Numbers stay Arabic, not 中文 | `30 日趋势`, `共 248 条` | `三十日趋势` |
| No emoji in product UI; one ✓ post-save: `已保存 ✓` | `已保存 ✓` | 🎉, 🚀, 👍 |
| You/I never appear — system speaks impersonally about the system | `请输入 Web UI 认证密钥` | `让我帮你输入密钥` |

### Casing

- English brand and acronyms keep canonical case: **Reaper115**, **Telegram**, **OpenAPI**, **SSE**, **Token**, **Vite**, **API**
- Product nouns in Chinese carry no decoration — no quotes, no brackets, no "official" suffixes
- File paths are full-width-free, monospaced, slash-prefixed: `/AV/涩花/无码字幕`

### Tone

Not playful, not corporate, not minimal-marketing. Think *router admin panel* or *Synology DSM* with the volume turned up on translucency. Hint text exists to teach the operator one thing in one breath, then disappears.

### Specific copy patterns

- Section headers are **2–4 Chinese characters**: `仪表盘` / `爬虫配置` / `离线任务` / `运行状态` / `路径`
- Page descriptions are one sentence under the H1, gray, no period: `资源入库、离线状态和最近抓取活动概览`
- Empty states say what's there in 4–8 chars: `暂无策略规则`, `暂无离线重试任务`, `没有匹配的资源`
- Error states are direct: `登录失败`, `请输入认证密钥`
- Buttons combine icon + 1–4 Chinese chars: `保存`, `添加版块`, `批量离线`, `开始爬取`

---

## VISUAL FOUNDATIONS

### Color

Seven brand tokens, all sourced from `design-delivery/Website/README.md` and confirmed against `web-ui/src/styles.css`:

| Token | Hex | HSL (light theme) | Usage |
| --- | --- | --- | --- |
| Primary | `#007AFF` | `211 100% 50%` | CTA, active nav, key data, links |
| Cyan | `#5ACBFA` | `198 94% 67%` | gradients, Telegram accent, decorative |
| Sky | `#B0D9FF` | `210 100% 84%` | icon highlights, soft tints |
| Mist | `#E5F2FF` | `210 100% 95%` | app icon and page background wash |
| White | `#FFFFFF` | `0 0% 100%` | glass surfaces (with alpha) |
| Ink | `#1C1C1E` | `240 3% 11%` | primary text, soft shadows |
| Slate | `#8E8E93` | `240 6% 57%` | secondary text |

**Semantic accents** (Apple system colors): success `#34C759`, warning `#FF9500`, destructive `#FF3B30`, info-purple `#5856D6`. Use the *background-tint @ 12%* + *foreground @ 100%* recipe — never solid filled badges.

**Dark theme** keeps the same identity but lowers everything by ~6 lightness points and shifts neutrals toward `218 39% 10%` body / `219 36% 14%` surface. White/border surfaces become `rgba(255,255,255,0.08–0.12)` — *the glass keeps glass-ness in the dark*.

### Type

Stack: `"SF Pro Display", Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.

No webfonts are bundled — Apple devices get SF Pro natively, others fall back to Inter. **No font files imported.** If you need pixel-fidelity exports on non-Apple platforms, add the open-licensed `Inter` family to `fonts/`.

| Style | Size / weight | Used for |
| --- | --- | --- |
| Display | 28 / 600 | Login mark only |
| Page H1 | 20 / 600 tracking-tight | `PageHeader.title` |
| Section H2 | 16 / 600 | Card headings |
| Body | 14 / 400 | Mobile body, dense table cells |
| Body emphasis | 14 / 500 | Active labels |
| Caption / hint | 12 / 400 | Hints, time stamps, table headers |
| Mono | 12–13 / 400 | API URL footer, file paths, regex |
| Mobile screen title | 20 | Mobile per-screen header |
| Mobile list title | 16 | Feature entry rows |

Letter-spacing: tight on H1 (`tracking-tight` ≈ −0.01em), zero everywhere else. No all-caps. Numbers tabular on dashboards (`30 日趋势`, `3,481`).

### Spacing & rhythm

8px grid; control heights are unusually compact for a web app (this is on purpose — the spec is "operational console", not "marketing site"):

- Buttons: **h-7 (28px)** sm, **h-8 (32px)** md, h-8 w-8 icon
- Inputs / Selects: **h-8 (32px)**
- Switch: **h-5 w-9 (20×36)**, knob h-4 w-4
- Sidebar nav row: **h-8** with 10px horizontal padding
- Header: **h-14 (56px)**
- Sidebar logo bar: **h-16 (64px)**
- Card padding: **16px** (`p-4`); status panel uses **20px** (`p-5`)

Gaps inside groups: 8 / 12 / 16. Page max width: `max-w-6xl` (1152px).

### Backgrounds

The **page background is the signature**. It is built from three stacked layers (see `colors_and_type.css → --bg-page`):

```
radial-gradient(circle at 18% 12%, rgba(90,203,250,0.25), transparent 28rem),
radial-gradient(circle at 82% 6%,  rgba(176,217,255,0.42), transparent 26rem),
linear-gradient(180deg, #FFFFFF 0%, #F0F7FF 42%, #F0F2F5 100%)
```

Two off-screen cyan/sky highlights bleed across the top of the viewport into a near-white field that fades to the cool Mac-window gray at the bottom. **Cards float on top of this** — never on flat white.

No hand-drawn illustrations. No repeating patterns. No textures. No grain. **No full-bleed photography.** Imagery, if any, is pixel-art icon work or screenshots framed inside glass cards.

### Glass (the headline effect)

Three intensities — pick the one that matches stacking depth:

| Layer | Background | Border | Shadow | Backdrop |
| --- | --- | --- | --- | --- |
| Sidebar / sticky header | `rgba(255,255,255,0.50–0.58)` | `rgba(255,255,255,0.60)` | `shadow-glass` | `blur(20px)` |
| Card | `rgba(255,255,255,0.58–0.62)` | `rgba(255,255,255,0.70)` | `shadow-panel` | `blur(20px)` |
| Inset row inside a card | `rgba(255,255,255,0.46)` | none | none | inherit |

Recipe in CSS:
```css
background: rgba(255,255,255,0.62);
border: 1px solid rgba(255,255,255,0.70);
backdrop-filter: blur(20px);
-webkit-backdrop-filter: blur(20px);
box-shadow: 0 18px 48px rgba(28,28,30,0.10);
border-radius: 8px;
```

In dark theme: substitute `rgba(255,255,255,0.10)` for the fill and `rgba(255,255,255,0.10)` for the border.

### Borders, radii, shadows

- **Radius:** `8px` is the *only* default. The logo and large brand surfaces are `16px` (`rounded-xl`) or `20px` (`rounded-2xl`). Pills (badges, switches) are fully rounded. **No 4px corners, no 12px corners** — sticking to the spec keeps the glass feeling consistent.
- **Borders:** always 1px and always semi-transparent white (`rgba(255,255,255,0.7)` light) or 10% white (`rgba(255,255,255,0.1)` dark). Hard `#000` borders never appear.
- **Shadows:**
  - `shadow-panel` — `0 18px 48px rgba(28,28,30,0.12)` — cards
  - `shadow-glass` — `0 24px 60px rgba(28,28,30,0.14)` — sidebar, login card
  - `shadow-cta` — `0 12px 28px rgba(0,122,255,0.28)` — primary buttons
  - `shadow-cta-hover` — `0 16px 36px rgba(0,122,255,0.34)` — primary on hover
  - `shadow-logo` — `0 10px 22px rgba(0,122,255,0.18)` — under the logo mark in the sidebar

### Hover, press, focus

- **Primary button hover:** `translate-y-[-2px]`, brighter blue `bg-primary/90`, deeper blue shadow
- **Primary button press:** `translate-y-0`, `bg-primary/80`, no shadow shift
- **Secondary / ghost hover:** background goes from `white/58` → `white/72`, slight `-2px` lift
- **Sidebar item active:** primary fill, primary-foreground text, blue `shadow-cta-light`
- **Sidebar item hover (inactive):** `bg-white/54`, text `→ foreground`
- **Focus:** `ring-2 ring-primary/40` (buttons), `ring-2 ring-primary/15 + border-primary/60` (inputs)
- **Disabled:** `opacity-40`, `cursor-not-allowed`, no shadow
- **Switch:** track tints primary, knob translates `+16px`

No bounce. No spring. **All transitions are 200ms `ease`** unless they're truly background-fade (then 300ms). Page-level mode/theme transitions: 200ms on `background-color`, none on `transform`.

### Transparency & blur — when

Use blur **only on glass surfaces that are visually elevated above the page background.** Inline rows inside a card *inherit* their parent's blur — they don't add a second one (multi-layer blur kills perf and looks muddy).

Never blur:
- The page background itself
- Text
- Icon glyphs
- Charts (Recharts gets a `backdrop-filter: blur(20px)` on its **tooltip**, not the chart)

### Iconography (in brief — full section in [ICONOGRAPHY](#iconography) below)

- Two icon systems run side-by-side. **Lucide** (open-source, stroke-based) drives every Tailwind page through `lucide-react`. **Custom brand icons** (the `function_size` SVGs/PNGs) drive the logo, the favicon, the Telegram bot avatar, and the marketing/feature-entry surfaces.
- Use Lucide for nav, controls, table actions. Use brand SVGs for product surfaces (Telegram intro card, mobile feature entries, app icon).

### Charts

Recharts only. Palette is fixed: `#007AFF, #5ACBFA, #B0D9FF, #34C759, #5856D6, #FF9500, #8E8E93`. Axes have `axisLine={false} tickLine={false}`, ticks `fontSize: 11, fill: #8F8F8F`. Lines are 2px stroke, **no dots**. Donuts use `innerRadius={60} outerRadius={105} paddingAngle={2}`.

### Layout rules

- One page = `<aside class="w-60">` fixed sidebar + `<main class="max-w-6xl px-6 py-6">`
- Sidebar collapses below `lg` (1024px) and is gated by a hamburger
- Cards never bleed to the viewport edge; always at least `px-6` of breathing room
- Tables have **no card chrome on the cells** — header has a single `border-b border-border`, rows `divide-y divide-border`. The card around them carries the chrome.
- Page header: H1 + description left, action buttons right. They wrap to two rows on narrow screens (`flex-col md:flex-row`).

---

## ICONOGRAPHY

### Two systems, one rule

1. **Custom brand icons** (`assets/icons/`) — used for product surfaces that need to *feel* like Reaper115:
   - the app icon / Telegram bot avatar (`logo/sehuatang-115-bot.svg`)
   - the favicon
   - mobile feature entry tiles (upload, download, share_link, cloud_115_file, settings, security, help, telegram)
2. **Lucide** (loaded via `lucide-react` in the codebase, mirrored via the Lucide CDN in this kit) — used for all admin-UI affordances: nav rows, table actions, form labels, status icons.

### Custom-icon spec

- File naming is strictly `function_size.{svg|png}` — `upload_24.svg`, `download_64.png`, `security_128.png`. Sizes 24 / 32 / 64 / 128 are always exported; SVG is always at 24.
- Visual style: **rounded-square tile, blue gradient or single color, white glyph**. Stroke style varies by function — telegram is a flat fill paper-plane, download / upload are flat fill arrows on solid tiles, security is a shield, etc.
- Backgrounds are colored in (not hollow). The 24px SVG is the *source of truth* — PNGs are exports.
- Used for *product identity*; never substitute Lucide here.

### Lucide spec (admin UI)

- Stroke-based, default 2px stroke, default `currentColor`
- Sizes: `h-3.5 w-3.5` inside compact buttons (14px), `h-4 w-4` in nav and badges (16px), `h-5 w-5` in section headers (20px), `h-8 w-8` in dashboard stat cards (32px)
- Specific glyphs in use: `Gauge` (Dashboard), `Sliders` (配置管理), `Settings2` (爬虫配置), `Database` (涩花数据), `ScrollText` (离线任务), `Activity` (爬取控制), `Menu` / `X` / `Sun` / `Moon` / `LogOut` (chrome), `BarChart3` / `CheckCircle2` / `Clock3` / `RotateCcw` (stat cards), `Search` / `Trash2` / `Download` / `Pencil` / `Plus` / `Save` / `XCircle` / `RefreshCw` / `Play` / `Radio` / `KeyRound` / `LogIn` / `ServerCog` / `FolderOpen` (actions)

### Emoji and unicode

- **Emoji are not used in the product UI.** Anywhere.
- Unicode chars used as visual marks: `✓` after save (`已保存 ✓`). That's the only one.
- Notification messages from the Telegram bot can include the cover image as a *photo attachment*, but no emoji decoration in the message body.

### What we couldn't bring in

- `StyleGuide.pdf` failed to import in the binary copy step — please re-attach the file directly so we can mine the typography ramps and spacing dimensions if they differ from the codebase.
- No webfont files were shipped with the brand pack. `SF Pro Display` ships with macOS / iOS only. **If you want pixel-perfect type on Linux/Windows or PDFs, please drop the Inter v4 woff2 family into `fonts/`** and we'll wire it through `colors_and_type.css`.

---

## Design system cards

Every card in `preview/` is registered as a reviewable asset and shows up in the Design System tab. Cards are split into:

- **Brand** — logo, favicon, app icon
- **Colors** — primary scale, neutrals, semantic accents, glass surfaces
- **Type** — display, page, body, mono specimens
- **Spacing** — radii, shadow ladder, control heights
- **Components** — buttons, inputs, switch, badge, status row, sidebar nav, page header, empty/loading/error states

Open the Design System tab to review them all together.

---

## UI kits

- **`ui_kits/web/`** — recreation of the `web-ui/` admin: Login, Dashboard (with status panel + stats + 30-day trend + section donut + recent table), Sehua Data (filter + table), Strategy (crawler config + rules CRUD + regex test), Tasks (retry queue), Crawl (date presets + SSE log stream). Click-thru navigation between pages; data is mocked but visually accurate.
- **`ui_kits/telegram/`** — Telegram chat surface as described in `Mobile/README.md`: bot avatar in header, intro card with command shortcuts, a sample `/csh_today` exchange ending in a notification card with cover image placeholder.

Open `ui_kits/<product>/index.html` for the click-thru prototype, or `*.jsx` for individual components.
