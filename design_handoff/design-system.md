# RecapAI Design System

> A reference document describing the visual language, component patterns, and UX philosophy of the RecapAI app. Generated from codebase analysis (templates, Tailwind config, custom CSS).

---

## Table of Contents

1. [Philosophy & Approach](#1-philosophy--approach)
2. [Technology Foundation](#2-technology-foundation)
3. [Color Palette](#3-color-palette)
4. [Typography](#4-typography)
5. [Spacing & Layout](#5-spacing--layout)
6. [Responsive Design](#6-responsive-design)
7. [Component Library](#7-component-library)
   - [Navigation](#71-navigation)
   - [Page Shell](#72-page-shell)
   - [Buttons](#73-buttons)
   - [Forms & Inputs](#74-forms--inputs)
   - [Cards](#75-cards)
   - [Badges & Tags](#76-badges--tags)
   - [Category Filter](#77-category-filter)
   - [Flash Messages / Alerts](#78-flash-messages--alerts)
   - [Article Detail Layout](#79-article-detail-layout)
   - [Sidebar](#710-sidebar)
   - [Loading / Processing State](#711-loading--processing-state)
   - [Info Boxes](#712-info-boxes)
   - [Pagination](#713-pagination)
8. [Icons](#8-icons)
9. [Interaction Patterns](#9-interaction-patterns)
10. [Accessibility](#10-accessibility)
11. [Design Tokens Quick Reference](#11-design-tokens-quick-reference)

---

## 1. Philosophy & Approach

RecapAI's design is **functional-first and deliberately simple**. The UI is a lightweight wrapper around content — it gets out of the way so the user can focus on their reading list.

Key principles visible throughout the codebase:

- **Utility-first**: Pure Tailwind CSS with minimal custom CSS. No component framework or CSS-in-JS — everything is composed from Tailwind utilities directly in Jinja2 templates.
- **System fonts**: No web font loading. The UI relies on the OS's native sans-serif stack, which is fast, readable, and familiar.
- **Color as signal**: Color is used sparingly and semantically. Blue = action, green = processing/success, red = danger. Gray runs are used for backgrounds and content hierarchy.
- **No unnecessary animation**: The only animation in the entire UI is a spinner for articles being classified by the AI pipeline. Everything else is static or uses simple CSS transitions.
- **Mobile-first responsive**: Layouts default to single-column/vertical on small screens and expand horizontally on medium (`md:`) breakpoints.
- **Progressive enhancement**: The article classification status updates via a polling `setInterval` with vanilla JS — no frontend framework required.

---

## 2. Technology Foundation

| Layer | Technology |
|-------|-----------|
| CSS framework | [Tailwind CSS](https://tailwindcss.com) (utility-first, JIT mode) |
| Custom CSS | `recap/static/css/input.css` — minimal `@apply` rules |
| Typography plugin | `@tailwindcss/typography` (for article prose content) |
| Template engine | Jinja2 (server-rendered HTML) |
| JavaScript | Vanilla JS (no framework; used for polling and filter toggle) |
| Icon set | Inline SVG (Heroicons style, `viewBox="0 0 24 24"`) |

**Tailwind config** (`tailwind.config.js`):
```js
module.exports = {
  content: ["./recap/templates/**/*.html"],
  theme: { extend: {} },   // no custom theme — uses Tailwind defaults
  plugins: [require('@tailwindcss/typography')],
}
```

The absence of theme extensions means the entire design system is built from **Tailwind's default palette and spacing scale** — no custom design tokens exist outside of component-level class composition.

---

## 3. Color Palette

All colors come from Tailwind's default palette. The app uses a narrow, purposeful subset.

### 3.1 Semantic Color Roles

| Role | Color | Tailwind token(s) | Usage |
|------|-------|-------------------|-------|
| **Primary action** | Blue | `blue-500`, `blue-600`, `blue-700` | Buttons, links, CTA |
| **Danger / destructive** | Red | `red-600`, `red-700` | Danger buttons (e.g. "Regenerate Token") |
| **Processing / success** | Green | `green-200`, `green-300` | Article processing state, flash messages |
| **Info / loading** | Blue-tinted | `blue-50`, `blue-700` | Info callout boxes |
| **Navigation** | Black | `black` (bg), `slate-200` (text) | Top nav bar |
| **Page background** | Near-white | `gray-50` | Body background |
| **Card / form background** | White | `white` | All card and form surfaces |
| **Sidebar / filter background** | Light gray | `gray-100`, `gray-200` | Sidebar, category filters, alternating rows |
| **Body text** | Dark gray | `gray-700`, `gray-800` | Primary readable text |
| **Secondary / meta text** | Medium gray | `gray-500`, `gray-600` | Author names, timestamps, hints |
| **Heading text** | Near-black | `gray-900` | Sidebar section headings |
| **Code / token display** | Light gray | `gray-100` | Monospace token display boxes |

### 3.2 Color Applications

**Backgrounds:**
```
bg-black         → navigation bar
bg-gray-50       → body / page background
bg-gray-100      → category badges, even sidebar rows, token code box
bg-gray-200      → sidebar, filter list items, alternate rows
bg-white         → cards, forms, article list container
bg-blue-50       → info callout (still-loading notice)
bg-blue-600      → primary button (article detail page)
bg-green-200     → processing article card, flash message
bg-green-300     → newly classified article card (injected by JS)
bg-red-600       → danger button
```

**Text:**
```
text-white       → buttons, nav
text-slate-200   → nav links (on black background)
text-slate-900   → flash message text
text-gray-500    → helper/hint text
text-gray-600    → secondary metadata (author names)
text-gray-700    → form labels, body text
text-gray-800    → article summary text
text-gray-900    → sidebar headings
text-blue-600    → global link color (defined in input.css)
text-blue-700    → info box text
```

**Borders:**
```
border-gray-300  → secondary/outline button borders
border (default) → form input borders (inherits Tailwind default: #e5e7eb)
```

### 3.3 Global Link Color

Defined in `input.css` as a global rule applied to all `<a>` elements:
```css
a {
  @apply text-blue-600 underline dark:text-blue-500 hover:no-underline
}
```
Navigation links **override** this with `text-slate-200 underline hover:no-underline` to work on the dark nav background.

---

## 4. Typography

### 4.1 Font Families

No web fonts are loaded. The full stack:

| Context | Stack |
|---------|-------|
| **UI (global)** | `ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` (Tailwind `font-sans` default) |
| **Code / token display** | `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` (Tailwind `font-mono`, applied via `font-mono` class on API token box) |

The global font is set in `input.css`:
```css
html { @apply font-sans }
```

### 4.2 Type Scale

| Size class | Approx px | Usage |
|------------|-----------|-------|
| `text-xs` | 12px | Small inline labels (source URL in cards, date display) |
| `text-sm` | 14px | Metadata, form inputs, button text, helper text, filter labels, article card secondary text |
| `text-base` | 16px | Body text, nav links |
| `text-lg` | 18px | Section headings (e.g. "Articles you have bookmarked") |
| `text-xl` | 20px | Navigation brand text |
| `text-2xl` | 24px | Article detail page title, page-level headings |

### 4.3 Font Weights

| Weight class | Usage |
|--------------|-------|
| `font-medium` | Navigation links |
| `font-semibold` | Sidebar section headings (`h2`), category badges |
| `font-bold` | Card article titles, page headings, button text, submit inputs |

### 4.4 Line Height & Spacing

| Class | Usage |
|-------|-------|
| `leading-tight` | Form inputs (compact text fields) |
| `leading-relaxed` | Article summary body text (improved readability) |

### 4.5 Typography Plugin (Prose)

Used on the article detail page to apply polished prose styling to AI-generated article summaries:

```html
<div class="prose prose-slate max-w-prose">
```

- `prose` — applies Tailwind typography defaults (heading hierarchy, paragraph spacing, list styles, etc.)
- `prose-slate` — tints the prose color scheme with slate tones (pairs with the gray/slate UI)
- `max-w-prose` — constrains the column to ~65ch (~672px), the typographically optimal line length for reading

**Note on paragraph breaks:** AI-generated summaries may contain `\n` characters. The template splits on `\n` and wraps each paragraph in a `<p>` tag rather than relying on `white-space: pre-wrap` or `| safe`:
```html
{% for para in article.summary.split('\n') %}
{% if para.strip() %}<p class="mb-4">{{ para }}</p>{% endif %}
{% endfor %}
```

---

## 5. Spacing & Layout

### 5.1 Spacing Scale

Tailwind's default 4px-base scale is used throughout. Commonly used values:

| Scale | px | Common usage |
|-------|----|--------------|
| `1` | 4px | Tight gaps, small icon margins |
| `2` | 8px | Form input padding, flash message padding |
| `3` | 12px | Button horizontal padding, nav padding |
| `4` | 16px | Card/section padding, sidebar padding |
| `6` | 24px | Section spacing (sidebar `space-y-6`, button gaps) |
| `8` | 32px | Large spacing (article summary bottom margin) |

### 5.2 Layout Approach

**Primary layout primitive: Flexbox.** The app uses CSS Grid nowhere — everything is composed from `flex`, `flex-row`, `flex-col`, `flex-wrap`, and alignment utilities.

**Two-column pattern (index page — article list + filter sidebar):**
```html
<div class="md:flex md:gap-6 md:items-start">
  <div class="flex-1 min-w-0 max-w-2xl"><!-- article list column --></div>
  <aside class="hidden md:block w-60 shrink-0 sticky top-4 self-start"><!-- filter sidebar --></aside>
</div>
```
- Article column is `max-w-2xl` (~672px) to keep the reading line comfortable on wide screens
- Sidebar is `w-60` (240px), `sticky top-4 self-start` so it stays in view while scrolling
- Sidebar is `hidden md:block` — invisible on mobile, always visible on desktop

**Two-column pattern (article detail):**
```html
<div class="flex flex-col md:flex-row gap-6">
  <div class="flex-1 min-w-[280px]"><!-- main content --></div>
  <div class="w-full md:w-[200px] md:min-w-[200px]"><!-- sidebar --></div>
</div>
```

**Full-width containers:**
```html
<main class="container mx-auto px-3 py-2">
```
The `container` class applies Tailwind's responsive max-widths. Content is centered with `mx-auto`.

**Responsive card containers:**
List/card areas use `w-full` (article list) or `w-full max-w-sm` (profile card, organize taxonomy) so they fill available width on any viewport rather than clamping to a fixed `384px`.

### 5.3 Arbitrary Values

A few custom sizes use Tailwind's arbitrary value syntax where the default scale doesn't fit:

| Class | Value | Usage |
|-------|-------|-------|
| `w-[180px]` | 180px | Narrower sidebar in some views |
| `w-[200px]` | 200px | Article detail sidebar |
| `md:min-w-[200px]` | 200px | Sidebar minimum on medium+ screens |
| `py-1.5` | 6px | Sidebar list item vertical padding |
| `max-w-[160px]` | 160px | Truncated source URL in article cards |

---

## 6. Responsive Design

### 6.1 Breakpoint Usage

The app uses two breakpoints from Tailwind's default scale:

| Breakpoint | Min-width | Usage |
|------------|-----------|-------|
| `sm:` | 640px | Button row changes from column to row in article detail |
| `md:` | 768px | Primary layout shift (single-column → two-column) |

Large (`lg:`) and extra-large (`xl:`) breakpoints are not used — the layout plateaus at the medium breakpoint.

### 6.2 Mobile-First Patterns

Templates default to vertical/single-column and apply horizontal/multi-column at `md:`:

```html
<!-- Index page: single-column on mobile, two-column on desktop -->
<div class="md:flex md:gap-6 md:items-start">

<!-- Index filter sidebar: hidden on mobile, persistent on desktop -->
<aside class="hidden md:block w-60 shrink-0 sticky top-4 self-start">

<!-- Index filter toggle button: visible on mobile only -->
<button class="md:hidden" onclick="showFilter();">

<!-- Article detail: stacks vertically on mobile, side-by-side on desktop -->
<div class="flex flex-col md:flex-row gap-6">

<!-- Article detail sidebar: full width on mobile, fixed 200px on desktop -->
<div class="w-full md:w-[200px] md:min-w-[200px]">

<!-- Action buttons: stacked on mobile, inline on small+ -->
<div class="flex flex-col sm:flex-row gap-4">
```

---

## 7. Component Library

### 7.1 Navigation

The global top navigation bar, defined in `base.html`.

```html
<nav class="flex flex-wrap items-center gap-y-1 font-medium bg-black text-slate-200 py-2 px-3">
  <div class="flex-1 min-w-0 text-xl">
    <b>Recap AI</b>: Summarize articles for reading later
  </div>
  <div class="flex gap-3 shrink-0 text-base">
    <a class="font-medium text-slate-200 underline hover:no-underline" href="...">Home</a>
    <a class="font-medium text-slate-200 underline hover:no-underline" href="...">Profile</a>
    <a class="font-medium text-slate-200 underline hover:no-underline" href="...">Logout</a>
  </div>
</nav>
```

**Characteristics:**
- Full-width black bar, no max-width constraint
- `flex-wrap` + `gap-y-1` — brand and links wrap to a second line on narrow viewports instead of overflowing
- Brand text: `flex-1 min-w-0 text-xl` — expands to fill available width, truncates cleanly if needed
- Nav links: `flex gap-3 shrink-0 text-base` — inline row that never shrinks below its natural width
- Links use `text-slate-200 underline hover:no-underline` — overriding the global `text-blue-600` link rule
- Authentication state is reflected: anonymous users see Login; authenticated users see Profile + Logout
- Theme color meta tag set to `#000000` — matches the nav bar (browser tab/mobile chrome tinting)

### 7.2 Page Shell

```html
<body class="min-h-screen bg-gray-50">
  <nav>...</nav>
  <!-- flash messages -->
  <main class="container mx-auto px-3 py-2">
    {% block content %}{% endblock %}
  </main>
  <footer class="mt-auto py-4 text-center text-sm text-gray-600">
    <p>&copy; {{ current_year }} Recap AI. All rights reserved.</p>
  </footer>
</body>
```

- `min-h-screen` ensures the body fills the viewport even on short pages
- `bg-gray-50` gives the page a very subtle off-white tone vs. pure white cards
- Main content is wrapped in a responsive `container` with modest padding
- Footer is centered, small, and uses muted gray text

### 7.3 Buttons

#### Primary Button (Blue)
Used for the main CTA on most pages.

```html
<button class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded focus:outline-none">
  Label
</button>
```

On the article detail page, a slightly different variant uses `blue-600` with `rounded-lg` and `transition-colors`:
```html
<a class="inline-flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
  <span>Read full article</span>
  <svg class="h-4 w-4 ml-2" .../>
</a>
```

**Profile action buttons** (Edit, Reclassify, API Token on profile page):
```html
<a class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-3 px-3 text-sm rounded focus:outline-none">
  Label
</a>
```
Uses `py-3` (12px vertical padding) to meet the 44px minimum touch target height on mobile.

**Small Primary Button** (pagination):
```html
<a class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-3 text-sm rounded focus:outline-none">
  Label
</a>
```

#### Secondary Button (Outline)
Used as the "Back" action alongside a primary CTA.

```html
<a class="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
  <svg class="h-4 w-4 mr-2" .../>
  <span>Back to articles</span>
</a>
```

#### Danger Button (Red)
Used for destructive, irreversible actions (e.g. regenerating an API token).

```html
<button class="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        onclick="return confirm('...')">
  Regenerate Token
</button>
```

Note: Danger buttons use a JS `confirm()` dialog as a safety gate before the action fires.

#### Disabled Button
Used to show a non-interactive loading state during article classification:

```html
<button type="button" class="bg-green-200 pt-1 pb-2" disabled>
  <svg class="animate-spin h-5 w-5 text-white" .../>
</button>
```

#### Button Summary Table

| Variant | Background | Hover | Text | Border | Shape | Padding |
|---------|-----------|-------|------|--------|-------|---------|
| Primary | `blue-500` | `blue-700` | white | none | `rounded` | `py-2 px-3` |
| Primary (detail page) | `blue-600` | `blue-700` | white | none | `rounded-lg` + `transition-colors` | `py-2 px-4` |
| Profile Actions (Edit/Reclassify/Token) | `blue-500` | `blue-700` | white `text-sm` | none | `rounded` | `py-3 px-3` (44px touch target) |
| Pagination | `blue-500` | `blue-700` | white `text-sm` | none | `rounded` | `py-2 px-3` |
| Secondary / Outline | transparent | `gray-50` | `gray-700` | `gray-300` | `rounded-lg` + `transition-colors` | `py-2 px-4` |
| Danger | `red-600` | `red-700` | white | none | `rounded` | `py-2 px-4` |
| Disabled / Loading | `green-200` | — | — | none | — | `pt-1 pb-2` |

### 7.4 Forms & Inputs

Form styling is applied globally via `@apply` rules in `input.css`, so no per-template class repetition is needed.

**Text & Password inputs:**
```css
input[type=text], input[type=password] {
  @apply shadow appearance-none border rounded py-2 px-2 my-2
         text-gray-700 leading-tight focus:outline-slate-500
}
```

- `shadow` — subtle drop shadow for depth
- `appearance-none border rounded` — resets browser defaults, adds consistent border and radius
- `py-2 px-2` — comfortable tap target
- `my-2` — vertical spacing between fields (using margin rather than gap)
- `text-gray-700 leading-tight` — readable, compact text
- `focus:outline-slate-500` — slate-colored focus ring (replaces the default blue browser outline)

**Submit inputs:**
```css
input[type=submit] {
  @apply bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded focus:outline-none
}
```
Identical visual to the Primary button. Uses `focus:outline-none` rather than the slate outline used by text inputs.

**Form containers** (login, register, add article, etc.):
```html
<div class="bg-white shadow-lg rounded px-2 pt-4 pb-4 mb-2">
  <form method="post">...</form>
</div>
```
Forms are wrapped in the standard white card shell. Fields are separated by `<p>` paragraph elements (no custom grid layout).

**Monospace display boxes** (API token display):
```html
<div class="bg-gray-100 rounded p-4 font-mono text-sm break-all mb-6">
  {{ token }}
</div>
```
Used for displaying read-only API tokens. `break-all` ensures long token strings wrap within the box.

### 7.5 Cards

Cards are the primary content container for articles.

**Standard article card** (classified article in list):
```html
<div class="bg-white shadow-lg rounded px-3 pt-3 pb-3 mb-2">
  <div class="flex justify-between items-start gap-2 mb-1">
    <b class="text-base leading-snug">{{ article.title }}</b>
    <span class="text-xs text-gray-500 whitespace-nowrap shrink-0">{{ article.created.strftime('%b %d, %Y') }}</span>
  </div>
  <!-- author (if present) -->
  <div class="text-sm text-gray-600 mb-1">{{ article.author_name }}</div>
  <!-- summary teaser (if present) -->
  <p class="text-sm text-gray-700 mb-2 line-clamp-2">{{ article.summary }}</p>
  <div class="flex justify-between items-center gap-2 mt-1">
    <span class="inline-block bg-gray-100 rounded-full px-2 py-0.5 text-xs font-semibold text-gray-700">{{ article.category }}</span>
    <div class="flex items-center gap-3">
      <span class="text-xs text-gray-400 truncate max-w-[160px]"><!-- source domain --></span>
      <a class="text-sm font-medium text-blue-600 hover:underline shrink-0" href="...">View &rarr;</a>
    </div>
  </div>
</div>
```

**Processing article card** (awaiting AI classification):
```html
<div class="bg-green-200 shadow-md rounded px-2" id="article-{{ job_id }}">
  <!-- spinner + "being summarized" message -->
</div>
```

**Newly classified card** (injected by JS after polling detects completion):
```html
<div class="bg-green-300 shadow-lg rounded px-2 pt-4 pb-4 mb-2">
  <!-- title, author, category, "View Summary" link -->
</div>
```

The green progression (`green-200` → `green-300`) is a subtle visual signal that an article moved from in-progress to complete. JS replaces the processing card with the completed card by prepending to `#article_container` and removing the old element by ID.

**Empty state** (when user has no bookmarks):
```html
<div class="text-center py-12 text-gray-500">
  <p class="text-lg font-medium mb-2">No bookmarks yet</p>
  <p class="text-sm">Paste a URL above to save and summarize your first article.</p>
</div>
```
Shown in place of the card list when `articles` is empty. Centered, muted, and prompts the user to add their first article.

**Card characteristics:**
- White (or green) background surface
- `shadow-lg` or `shadow-md` drop shadow creates elevation/lift
- `rounded` corners (4px default Tailwind border-radius)
- `px-3 pt-3 pb-3 mb-2` padding/margin rhythm
- Bottom margin (`mb-2`) stacks cards with a small gap
- Cards are scannable: title + date on top row, author below, 2-line summary teaser (`line-clamp-2`), category badge + source URL + action link on bottom row

### 7.6 Badges & Tags

Used for article category labels.

```html
<div class="inline-block bg-gray-100 rounded-full px-3 py-1 text-sm font-semibold text-gray-700 mb-6">
  {{ article.category }}
</div>
```

- `rounded-full` — fully pill-shaped
- `inline-block` — fits content width
- `bg-gray-100` — very light gray tint, unobtrusive
- `text-sm font-semibold` — legible but not dominant
- `text-gray-700` — medium gray, reads as a secondary label

### 7.7 Category Filter

The filter panel has two distinct presentations depending on viewport width.

**Mobile (below `md:` / 768px) — toggle behavior:**

The funnel button and label are visible; tapping either toggles the filter panel open/closed via JS.

```html
<!-- Both elements are md:hidden — invisible on desktop -->
<button onclick="showFilter();" class="md:hidden">
  <svg class="size-6" .../><!-- funnel icon -->
</button>
<span onclick="showFilter();" class="text-sm align-text-top md:hidden">
  {% if request.args.get('category') %} Filtered by: {{ category }} {% else %} Filter your Articles. {% endif %}
</span>

<!-- Mobile toggle panel — starts hidden, JS toggles it -->
<div class="container w-full max-w-sm p-2 hidden" id="filter">
  <ul class="flex flex-row flex-wrap text-sm text-center">
    <li class="flex-1 h-12 m-1 p-1 bg-gray-200 text-sm"><a href="...">All</a></li>
    <li class="flex-1 h-12 m-1 p-1 bg-gray-200 text-sm text-center"><a href="...">Category (N)</a></li>
  </ul>
</div>
```

**Desktop (`md:` and above) — persistent sidebar:**

The toggle button and `#filter` panel are both invisible. The same category list is always visible in a sticky right sidebar defined in `index.html` (outside `_article.html`):

```html
<aside class="hidden md:block w-60 shrink-0 sticky top-4 self-start">
  <div class="text-sm font-semibold text-gray-700 mb-2 px-1">Filter Articles</div>
  <ul class="flex flex-row flex-wrap text-sm text-center">
    <li class="flex-1 h-12 m-1 p-1 bg-gray-200 text-sm"><a href="...">All</a></li>
    <li class="flex-1 h-12 m-1 p-1 bg-gray-200 text-sm text-center"><a href="...">Category (N)</a></li>
  </ul>
</aside>
```

**Filter tile characteristics (both contexts):**
- Items are `flex-1` — share the row width equally
- `text-sm` (14px) throughout
- Fixed `h-12` height ensures consistent tile sizing regardless of label length
- `m-1 p-1` creates a tight grid of filter tiles
- `bg-gray-200` background on each tile

### 7.8 Flash Messages / Alerts

Displayed at the top of every page when present (between nav and main content). Messages are rendered with categories so errors and successes display distinctly.

```html
{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}
<div class="px-2 py-2 my-2 mx-2 text-base space-y-1" id="flash">
  {% for category, message in messages %}
  <div class="rounded-xl px-3 py-2 {% if category == 'error' %}bg-red-100 text-red-900{% else %}bg-green-200 text-slate-900{% endif %}">
    {{ message | safe }}
  </div>
  {% endfor %}
</div>
{% endif %}
{% endwith %}
```

**Message categories:**

| Category | Background | Text | Used for |
|----------|-----------|------|----------|
| `'error'` | `bg-red-100` | `text-red-900` | Invalid credentials, article not found, exceptions |
| default (`'message'`) | `bg-green-200` | `text-slate-900` | Classification started, saved, reclassified, deleted |

**Flash calls with `'error'` category** (in `routes.py` and `auth/__init__.py`):
```python
flash('Article not found', 'error')
flash('General Exception', 'error')
flash('Invalid username or password', 'error')
```
All other `flash()` calls use the default category (rendered green).

- `rounded-xl` — more aggressively rounded corners than cards (`rounded`)
- `mx-2 my-2` — inset from screen edges, visually separated from nav and content
- `text-base` — standard body size, not emphasised via size increase
- The `#flash` ID is also targeted by JS: after an article finishes classifying, the JS replaces the flash content with a "Done classifying X" message via `flash.replaceChildren()`

**Info callout box** (article still loading state):
```html
<div class="p-4 bg-blue-50 text-blue-700 rounded-lg">
  <p>We are still reading the article at {{ url }}. Check back in ~20 seconds.</p>
</div>
```
Distinct from flash messages: inline within page content, blue-themed, indicates a waiting/info state.

### 7.9 Article Detail Layout

The most complex layout in the app — a two-column responsive layout with prose content and a metadata sidebar.

```
┌─────────────────────────────────────────────────────────┐
│ container mx-auto overflow-x-auto                       │
│  ┌──────────────────────────────┐  ┌────────────────┐  │
│  │ flex-1 min-w-[280px]         │  │ w-[200px]      │  │
│  │                               │  │ bg-gray-200    │  │
│  │ prose prose-slate max-w-none  │  │ rounded-lg p-4 │  │
│  │                               │  │                │  │
│  │ h1 (title)                    │  │ Sub-Categories │  │
│  │ p  (author)                   │  │ ─────────────  │  │
│  │ badge (category)              │  │ • item         │  │
│  │ div (summary)                 │  │ • item         │  │
│  │                               │  │                │  │
│  │ [Read article] [← Back]       │  │ Key Topics     │  │
│  │                               │  │ ─────────────  │  │
│  └──────────────────────────────┘  │ • item         │  │
│                                     └────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Key layout classes:**
- Outer: `flex flex-col md:flex-row gap-6`
- Content column: `flex-1 min-w-0 px-4`
- Sidebar: `w-full md:w-[200px] md:min-w-[200px] bg-gray-200 rounded-lg p-4`

On mobile: both columns are full-width and stack vertically. On desktop (`md:`): they sit side-by-side with a `gap-6` (24px) gutter.

**Content column rationale:** `flex-1 min-w-0` lets the column expand to fill all space not used by the sidebar. The previous `md:w-[280px] flex-shrink-0` conflicted with `flex-1` and pinned the column to a narrow fixed width on desktop.

### 7.10 Sidebar

Used in the article detail page for sub-categories and key topics.

```html
<div class="w-full md:w-[200px] md:min-w-[200px] bg-gray-200 rounded-lg p-4" name="sidebar">
  <div class="space-y-6">
    <div>
      <h2 class="font-semibold text-gray-900 mb-3">Sub-Categories</h2>
      <ul class="space-y-1">
        <li class="break-words px-2 py-1.5 odd:bg-white even:bg-gray-100 rounded">item</li>
      </ul>
    </div>
    <div>
      <h2 class="font-semibold text-gray-900 mb-3">Key Topics</h2>
      <ul class="space-y-1">
        <li class="break-words px-2 py-1.5 odd:bg-white even:bg-gray-100 rounded">item</li>
      </ul>
    </div>
  </div>
</div>
```

- `space-y-6` separates the two sections (Sub-Categories, Key Topics)
- `space-y-1` keeps list items close together
- `odd:bg-white even:bg-gray-100` — alternating zebra-stripe rows for readability
- `break-words` prevents long words (URLs, compound terms) from overflowing the 200px column
- `py-1.5` — slightly more vertical padding than the default `py-1`

### 7.11 Loading / Processing State

When an article has been submitted but not yet classified by the AI pipeline:

```html
<div class="bg-green-200 shadow-md rounded px-2" id="article-{{ job_id }}">
  <div>
    <button type="button" class="bg-green-200 pt-1 pb-2" disabled>
      <svg class="animate-spin ml-1 mr-1 h-5 w-5 text-white" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="#000066" stroke-width="4"/>
        <path class="opacity-75" fill="#000066" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4..."/>
      </svg>
    </button>
    Your article is being summarized.
    ...
  </div>
</div>
```

- The entire card is green (`bg-green-200`) — visually distinct from white classified cards
- `animate-spin` rotates the SVG spinner continuously
- The spinner uses `#000066` (a dark navy/indigo) — not a Tailwind utility class, an inline stroke color
- The button is `disabled` — prevents any click interaction
- A `setInterval` polls `/job/{job_id}/show` every 500ms; on completion, the card is replaced with the classified version

### 7.12 Info Boxes

Informational callouts that appear inline in page content (not flash messages).

**Processing/loading info** (article still being fetched):
```html
<div class="p-4 bg-blue-50 text-blue-700 rounded-lg">
  <p>We are still reading the article at {{ url }}. Check back in ~20 seconds.</p>
</div>
```

Characteristics:
- `bg-blue-50` — very pale blue, softer than the green flash
- `text-blue-700` — medium-dark blue, high contrast against pale background
- `rounded-lg` — more rounded than the standard `rounded` used on cards
- `p-4` — generous padding on all sides

### 7.13 Pagination

Appears at the bottom of the article list, right-aligned.

```html
<div class="float-right my-1">
  {% if prev_url %}
  <a href="{{ prev_url }}" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded focus:outline-none">
    Newer Articles
  </a>
  {% endif %}
  {% if next_url %}
  <a href="{{ next_url }}" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-3 rounded focus:outline-none">
    Older Articles
  </a>
  {% endif %}
</div>
```

- Uses `float-right` (not flex) — a legacy layout approach
- Pagination links use full Primary button styling (not link style)
- Labels are "Newer Articles" / "Older Articles" — time-ordered, not numeric page numbers

---

## 8. Icons

All icons are inline SVGs. The style matches [Heroicons](https://heroicons.com) (outline variant):

- `xmlns="http://www.w3.org/2000/svg"`
- `viewBox="0 0 24 24"`
- `fill="none"` with `stroke="currentColor"` (outline icons inherit text color)
- `stroke-linecap="round" stroke-linejoin="round"` (soft, rounded path ends)
- `stroke-width="1.5"` or `stroke-width="2"`

### Icon Sizing

| Class | px | Usage |
|-------|----|-------|
| `size-6` | 24×24px | Filter/funnel button icon |
| `h-5 w-5` | 20×20px | Loading spinner |
| `h-4 w-4` | 16×16px | Button inline icons (external link, back arrow) |

### Icon Spacing

Icons inside buttons use `ml-2` (trailing) or `mr-2` (leading) to separate from button text.

### Icon Examples

| Name | Location | Description |
|------|----------|-------------|
| Funnel/filter | `_article.html` | Toggles the category filter panel |
| Animated spinner | `_article.html` | Processing state; uses `animate-spin` |
| External link | `article/show.html` | "Read full article" button |
| Arrow left | `article/show.html` | "Back to articles" button |

---

## 9. Interaction Patterns

### 9.1 Article Classification Polling

The most complex interaction in the app. When an article is in the processing state:

1. A `setInterval` fires `checkJobStatus(job_id, article_id)` every **500ms**
2. Each tick fetches `/job/{job_id}/show` and checks `status`
3. On `"finished"`: clears the interval, fetches `/{{ article_id }}/show` for article JSON, builds a new card DOM element, prepends it to `#article_container`, removes the old spinner card, and updates the flash banner
4. Input validation (GUID format for job_id, integer for article_id) runs before each fetch

### 9.2 Category Filter Toggle

A simple show/hide toggle with no animation, **active on mobile only**.

```js
function showFilter() {
  let filter_element = document.getElementById("filter");
  if (filter_element.classList.contains("hidden")) {
    filter_element.classList.remove("hidden");
    filter_element.classList.add("visible");
  } else {
    filter_element.classList.remove("visible");
    filter_element.classList.add("hidden");
  }
}
```

The `#filter` panel starts `hidden`. Clicking the funnel icon or the label text calls `showFilter()`. No animation or transition.

On desktop (`md:` and above), the funnel button and label are `md:hidden` so `showFilter()` is never reachable — the `#filter` panel stays hidden and the persistent sidebar in `index.html` serves as the filter UI instead.

### 9.3 Danger Confirmation

Destructive actions (API token regeneration) use a native browser `confirm()` dialog:

```html
<button onclick="return confirm('Regenerate token? Your existing token will stop working immediately.')">
  Regenerate Token
</button>
```

If the user clicks Cancel, `confirm()` returns `false` and the form submission is prevented.

### 9.4 Link Behavior

- Navigation links: underlined, remove underline on hover (`hover:no-underline`)
- Body links (global rule): `text-blue-600 underline hover:no-underline`
- Buttons styled as links: `bg-blue-500 ... rounded` — visually a button even when using `<a>` tags

### 9.5 Category Filtering

Filtering is entirely server-side. Clicking a category in the filter panel navigates to `/?category={{ category }}`. No client-side filtering or state management.

---

## 10. Accessibility

### What's Present
- Semantic HTML: `<nav>`, `<main>`, `<footer>` landmark elements in every page
- `<html lang="en">` declared
- Viewport meta tag with `width=device-width, initial-scale=1.0`
- Form labels associated with inputs via Jinja WTForms (`{{ form.field.label }}`)
- Focus ring on text inputs (`focus:outline-slate-500`)
- Disabled attribute on processing-state buttons
- Underlined links with visible hover state change
- High contrast nav: near-white text on black background

### Areas for Improvement
- Nav links override focus outline with `focus:outline-none` not set — but the global link rule doesn't set it either; browser default focus ring would apply
- Flash messages don't use ARIA `role="alert"` or `aria-live="polite"` for screen reader announcement
- The loading spinner SVG has no `aria-label` or `role` for screen readers
- The filter toggle button has no `aria-expanded` attribute
- Color contrast: some gray-on-gray combinations (e.g. `text-gray-600` on `bg-gray-100`) may fall below WCAG AA 4.5:1 for small text

---

## 11. Design Tokens Quick Reference

Since Tailwind's default scale is used without extensions, these are aliases into the Tailwind defaults:

### Colors

| Token | Hex | Tailwind Class |
|-------|-----|----------------|
| Primary | `#3b82f6` | `blue-500` |
| Primary Dark | `#1d4ed8` | `blue-700` |
| Primary Alt | `#2563eb` | `blue-600` |
| Danger | `#dc2626` | `red-600` |
| Danger Dark | `#b91c1c` | `red-700` |
| Success/Processing | `#bbf7d0` | `green-200` |
| Success Complete | `#86efac` | `green-300` |
| Nav BG | `#000000` | `black` |
| Nav Text | `#e2e8f0` | `slate-200` |
| Page BG | `#f9fafb` | `gray-50` |
| Card BG | `#ffffff` | `white` |
| Sidebar BG | `#e5e7eb` | `gray-200` |
| Badge BG | `#f3f4f6` | `gray-100` |
| Body Text | `#374151` | `gray-700` |
| Secondary Text | `#4b5563` | `gray-600` |
| Muted Text | `#6b7280` | `gray-500` |
| Heading Text | `#111827` | `gray-900` |
| Link | `#2563eb` | `blue-600` |
| Border | `#d1d5db` | `gray-300` |
| Flash BG (success) | `#bbf7d0` | `green-200` |
| Flash Text (success) | `#0f172a` | `slate-900` |
| Flash BG (error) | `#fee2e2` | `red-100` |
| Flash Text (error) | `#7f1d1d` | `red-900` |
| Info BG | `#eff6ff` | `blue-50` |
| Info Text | `#1d4ed8` | `blue-700` |

### Spacing

| Token | Value | Class |
|-------|-------|-------|
| XS | 4px | `1` |
| SM | 8px | `2` |
| MD | 12px | `3` |
| LG | 16px | `4` |
| XL | 24px | `6` |
| 2XL | 32px | `8` |

### Border Radius

| Usage | Class | Approx radius |
|-------|-------|---------------|
| Standard cards, inputs | `rounded` | 4px |
| Sidebar, info boxes, buttons (detail page) | `rounded-lg` | 8px |
| Flash messages | `rounded-xl` | 12px |
| Badges / pills | `rounded-full` | 9999px |

### Shadows

| Usage | Class |
|-------|-------|
| Cards (classified) | `shadow-lg` |
| Cards (processing) | `shadow-md` |
| Form inputs | `shadow` (small) |

---

*Document generated: 2026-04-25. Updated: 2026-04-25 to reflect UX improvements from `ux-reading-improvements` branch (responsive widths, nav wrapping, card redesign, flash message categories, prose max-width, touch targets, filter bar font size, two-column desktop layout with persistent filter sidebar).*
