# Handoff: Recap AI — Homepage Redesign & App UX

## Overview

This package contains high-fidelity HTML design references for a full UX redesign of **Recap AI** — a personal web bookmarking and AI summarisation app built with Flask + Jinja2 + Tailwind CSS.

The primary deliverable is a **new unauthenticated homepage** that communicates the product value and drives sign-ups. Secondary deliverables cover improved UX for the authenticated article list, article detail, profile, login, and register pages.

---

## About the Design Files

The `.html` files in this bundle are **design references created as HTML prototypes** — they show the intended look, layout, and content but are **not production code to copy directly**. They use inline React/JSX for rapid prototyping and do not use Tailwind classes.

Your task is to **recreate these designs in the existing Flask + Jinja2 + Tailwind CSS codebase**, using the established patterns documented in `design-system.md`. Match the visual output as closely as possible using Tailwind utility classes, not inline styles.

---

## Fidelity

**High-fidelity.** These are pixel-close mockups with final colours, typography, spacing, layout, and copy. Recreate them faithfully using Tailwind utilities from the existing design system.

---

## Tech Stack (existing codebase)

| Layer | Technology |
|-------|-----------|
| Backend | Python / Flask |
| Templates | Jinja2 |
| CSS | Tailwind CSS (JIT, CDN or compiled via `tailwind.config.js`) |
| JS | Vanilla JS only — no framework |
| Icons | Inline SVG (Heroicons outline style) |

Tailwind config uses **no custom theme extensions** — all tokens are from Tailwind's default palette. The `@tailwindcss/typography` plugin is installed for prose content.

---

## Screens / Views

### 1. Homepage — Unauthenticated (`index.html` when `current_user.is_anonymous`)

**Purpose:** Marketing landing page. Communicates product value, drives account creation, and provides an easy path to login.

**Currently:** Shows only `<h1>Hello and Welcome!</h1>` and a placeholder message. Replace entirely.

#### Layout (mobile-first, single column → two-column at `md:`)

```
┌─────────────────────────────────────────────────────┐
│ NAV — black bar, "Recap AI" left, Login + CTA right │
├─────────────────────────────────────────────────────┤
│ HERO — dark/black bg                                │
│  Left: eyebrow label + h1 + subheading + CTA row    │
│  Right (md+): mock article cards stack              │
├─────────────────────────────────────────────────────┤
│ VALUE PILLARS — 3 columns (md+), stacked (mobile)   │
│  Save · Summarise · Discover                        │
├─────────────────────────────────────────────────────┤
│ HOW IT WORKS — 3-step horizontal row (md+)          │
├─────────────────────────────────────────────────────┤
│ SIGN-UP CTA SECTION — blue gradient bg              │
│  Centred heading + inline sign-up form card         │
├─────────────────────────────────────────────────────┤
│ FOOTER                                              │
└─────────────────────────────────────────────────────┘
```

#### Hero Section

- **Background:** `bg-black`
- **Padding:** `px-5 py-10 md:px-16 md:py-20`
- **Layout:** `flex flex-col md:flex-row gap-8 md:gap-12 items-center`

**Left column** (`flex-1`):
- Eyebrow: `text-blue-400 text-xs font-semibold uppercase tracking-widest mb-3` — "Your personal reading memory"
- H1: `text-4xl md:text-5xl font-extrabold text-white leading-tight tracking-tight` — "Bookmark it. Recap will remember it."
- Subheading `p`: `text-slate-400 text-base md:text-lg leading-relaxed mt-4 mb-7 max-w-lg` — "Save any article from the web. Recap summarises it, organises it, and delivers a weekend digest for your morning coffee — all automatically."
- CTA row: `flex flex-wrap gap-3 items-center`
  - Primary button: `bg-blue-500 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors` — "Create free account →" → links to `url_for('auth.register')`
  - Secondary link: `text-slate-400 text-sm underline hover:no-underline` — "Already have an account? Sign in" → links to `url_for('auth.login')`

**Right column** — mock article cards (desktop only: `hidden md:flex flex-col gap-3 w-80 shrink-0`):
- 3 stacked cards with decreasing opacity (`opacity-100`, `opacity-80`, `opacity-60`)
- Each card: `bg-gray-900 rounded-xl p-3 border border-gray-800`
  - Title: `text-gray-100 font-semibold text-sm mb-1`
  - Summary snippet: `text-gray-400 text-xs leading-relaxed`
  - Category badge: `inline-block bg-gray-800 text-blue-400 rounded-full px-2 py-0.5 text-xs font-semibold mt-2`
- Sample cards (use these exact titles for realistic feel):
  1. "The Future of AI in Healthcare" / Technology / "Researchers are exploring how LLMs can assist in early diagnosis…"
  2. "Why Deep Work Matters More Than Ever" / Productivity / "Cal Newport argues that focused work is the competitive advantage…"
  3. "Mediterranean Diet: New Findings" / Health / "A 10-year study confirms significant reduction in cardiovascular…"
- Caption below: `text-center text-gray-600 text-xs mt-2` — "Your personalised reading library"

#### Value Pillars Section

- **Background:** `bg-gray-50`
- **Padding:** `px-5 py-10 md:px-16 md:py-14`
- Section heading: `text-2xl md:text-3xl font-bold text-gray-900 mb-2` — "Everything you want to read. Actually remembered."
- Section sub: `text-gray-500 text-sm mb-8` — "Stop losing links in browser tabs and bookmarks folders."
- Grid: `grid grid-cols-1 md:grid-cols-3 gap-5`

Each pillar card: `bg-white rounded-xl p-5 shadow-sm`
- Icon box: `w-10 h-10 rounded-lg flex items-center justify-center mb-3`
- Title: `font-bold text-sm text-gray-900 mb-2`
- Body: `text-gray-500 text-sm leading-relaxed`

| Pillar | Icon bg | Heroicon | Title | Body |
|--------|---------|----------|-------|------|
| 1 | `bg-blue-50` | bookmark (outline) stroke `text-blue-500` | Save from anywhere | Paste a URL, use our Chrome extension, or share from your iPhone. Recap captures it instantly. |
| 2 | `bg-green-50` | clock (outline) stroke `text-green-500` | AI summaries in seconds | Every article is summarised and categorised automatically. Scan the key ideas without reading the full piece. |
| 3 | `bg-yellow-50` | magnifying-glass (outline) stroke `text-yellow-500` | Find it when you need it | Filter by your personal knowledge taxonomy. Get a weekly digest every weekend morning. |

#### How It Works Section

- **Background:** `bg-white`
- **Padding:** `px-5 py-10 md:px-16 md:py-14`
- Heading: `text-2xl font-bold text-gray-900 mb-2` — "How it works"
- Sub: `text-gray-500 text-sm mb-8` — "Three steps. Zero effort after setup."
- Steps: `flex flex-col md:flex-row gap-6`

Each step: `flex gap-4 items-start flex-1`
- Number bubble: `w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold text-sm shrink-0`
- Title: `font-bold text-sm text-gray-900 mb-1`
- Body: `text-gray-500 text-sm leading-relaxed`

| # | Title | Body |
|---|-------|------|
| 1 | Bookmark | Paste a URL or click "Save to Recap" in Chrome. Takes 2 seconds. |
| 2 | Recap reads it | Our AI reads the full article and writes a clear summary, adding it to your knowledge library. |
| 3 | Review & discover | Browse summaries, filter by category, and get your weekend reading digest automatically. |

#### Sign-Up CTA Section

- **Background:** use inline style `background: linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 100%)` (no Tailwind gradient equivalent for this exact look)
- **Padding:** `px-5 py-14 md:py-20 text-center`
- Heading: `text-white text-2xl md:text-3xl font-extrabold mb-2` — "Start building your reading memory"
- Sub: `text-blue-200 text-sm mb-7` — "Free to use. Your data is private by default."

Form card: `bg-white rounded-xl p-6 max-w-sm mx-auto shadow-2xl text-left`
- Card heading: `font-bold text-lg text-gray-900 mb-1` — "Create your account"
- Card sub: `text-sm text-gray-500 mb-5` — "Already have one? <a href="{{ url_for('auth.login') }}" class="text-blue-600 underline">Sign in</a>"
- Fields (use WTForms register form): username, email, password — styled via existing `input.css` global rules (they already apply `shadow appearance-none border rounded py-2 px-2 my-2 text-gray-700 leading-tight focus:outline-slate-500`)
- Submit: `w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-3 rounded-lg transition-colors` — "Create free account →"
- Privacy note: `text-xs text-gray-400 text-center mt-3` — "🔒 Your reading history is private by default."

#### Navigation (update `base.html`)

Update the nav for anonymous users to show a stronger CTA:
```html
{% if current_user.is_anonymous %}
<a href="{{ url_for('auth.login') }}"
   class="font-medium text-slate-200 underline hover:no-underline">Login</a>
<a href="{{ url_for('auth.register') }}"
   class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-1 px-3 rounded text-sm">
  Create Account →
</a>
{% else %}
<!-- existing profile + logout links unchanged -->
{% endif %}
```

---

### 2. Login Page (`auth/login.html`)

**Purpose:** Sign in existing users. Currently bare — give it a proper branded card.

**Layout:** Centred card, full-page `bg-gray-50`, padded `py-10`

Card: `bg-white rounded-xl shadow-md px-6 py-7 max-w-sm mx-auto`
- Logo line: `font-black text-xl text-gray-900 mb-1` — "Recap AI"
- H1: `text-2xl font-extrabold text-gray-900 mb-1` — "Welcome back"
- Sub: `text-sm text-gray-500 mb-6` — "Don't have an account? <a href="register" class="text-blue-600 underline">Create one free →</a>"
- Use existing WTForms field rendering; wrap in `<div class="mb-4">` per field
- Submit: `w-full` (via `input[type=submit]` global rule, already blue)
- Below form: `flex justify-between mt-4 text-sm`
  - Forgot password link (left)
  - Register link (right)

---

### 3. Register Page (`auth/register.html`)

Same card treatment as login.
- H1: "Create your account"
- Sub: "Already have one? Sign in"
- Fields: username, email, password
- Submit button full width
- Privacy note below: `text-xs text-gray-400 text-center mt-3` — "🔒 Your reading history is private by default."

---

### 4. App Home — Article List (`index.html` authenticated block)

Minor improvements to the existing layout:

**URL paste box** — add a heading label:
```html
<h1 class="font-bold text-base text-gray-900 mb-2">Save a new article</h1>
```

**Mobile filter pills** — replace the toggle+panel pattern with a horizontal scroll row (mobile only):
```html
<div class="flex gap-2 overflow-x-auto pb-2 md:hidden">
  <a href="{{ url_for('routes.index') }}"
     class="bg-blue-500 text-white rounded-full px-4 py-1.5 text-xs font-semibold shrink-0">All</a>
  {% for grouping in groupings %}
  <a href="{{ url_for('routes.index', category=grouping.category) }}"
     class="bg-gray-200 text-gray-700 rounded-full px-4 py-1.5 text-xs font-semibold shrink-0">
    {{ grouping.category }}
  </a>
  {% endfor %}
</div>
```

**Desktop sidebar filter** — improve active state styling. Add active category highlight:
```html
<li class="{% if request.args.get('category') == grouping.category %}bg-blue-100 text-blue-700 font-semibold{% else %}bg-gray-200{% endif %} ...">
```

---

### 5. Article Detail (`article/show.html`)

Add **previous / next article navigation** at the bottom of the content column.

In `routes.py`, pass `prev_article` and `next_article` to the template (fetch the articles immediately before and after the current one by `created` timestamp for the current user).

Template addition (below the action buttons `div`):
```html
{% if prev_article or next_article %}
<div class="border-t border-gray-200 pt-4 mt-6 flex gap-3">
  {% if prev_article %}
  <a href="{{ url_for('routes.show', id=prev_article.id) }}"
     class="flex-1 bg-white border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors">
    <span class="text-xs text-gray-400 block mb-1">← Previous</span>
    <span class="text-sm font-semibold text-gray-900 leading-snug">{{ prev_article.title }}</span>
  </a>
  {% endif %}
  {% if next_article %}
  <a href="{{ url_for('routes.show', id=next_article.id) }}"
     class="flex-1 bg-white border border-gray-200 rounded-lg p-3 text-right hover:bg-gray-50 transition-colors">
    <span class="text-xs text-gray-400 block mb-1">Next →</span>
    <span class="text-sm font-semibold text-gray-900 leading-snug">{{ next_article.title }}</span>
  </a>
  {% endif %}
</div>
{% endif %}
```

**Route change needed** in `routes.py` `show()` function:
```python
# After fetching article:
prev_article = Article.query.filter(
    Article.user_id == current_user.id,
    Article.created > article.created,
    Article.classified.isnot(None)
).order_by(Article.created.asc()).first()

next_article = Article.query.filter(
    Article.user_id == current_user.id,
    Article.created < article.created,
    Article.classified.isnot(None)
).order_by(Article.created.desc()).first()

return render_template('article/show.html',
    article=article,
    prev_article=prev_article,
    next_article=next_article)
```

---

### 6. Profile Page (`profile/user.html`)

**Remove the `{% include '_article.html' %}` line** — the article list should not appear on the profile page.

Replace the card with a cleaner layout:

```html
<!-- Avatar + user info header -->
<div class="flex items-center gap-4 mb-7">
  <div class="w-14 h-14 rounded-full bg-blue-700 flex items-center justify-center text-white font-black text-2xl shrink-0">
    {{ user.username[0].upper() }}
  </div>
  <div>
    <div class="font-extrabold text-xl text-gray-900">{{ user.username }}</div>
    <div class="text-sm text-gray-500">{{ user.email }}</div>
  </div>
</div>

<!-- Section label -->
<div class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Account settings</div>

<!-- Action cards -->
{% for action in [
  {'href': url_for('profile.edit_profile'),      'title': 'Edit Profile',         'desc': 'Update your email and phone number',      'icon_color': 'bg-blue-50',   'icon': 'person'},
  {'href': url_for('profile.organize_taxonomy'), 'title': 'Reclassify Articles',  'desc': 'Reorganise your knowledge taxonomy',       'icon_color': 'bg-green-50',  'icon': 'list'},
  {'href': url_for('profile.api_token'),         'title': 'API Token',            'desc': 'Generate a token for integrations',        'icon_color': 'bg-yellow-50', 'icon': 'key'},
] %}
<a href="{{ action.href }}"
   class="flex items-center gap-4 bg-white rounded-xl p-4 shadow-sm mb-3 hover:shadow-md transition-shadow">
  <div class="w-10 h-10 rounded-lg {{ action.icon_color }} flex items-center justify-center shrink-0">
    <!-- Insert appropriate Heroicon SVG for action.icon -->
  </div>
  <div class="flex-1 min-w-0">
    <div class="font-semibold text-sm text-gray-900">{{ action.title }}</div>
    <div class="text-xs text-gray-500">{{ action.desc }}</div>
  </div>
  <!-- Heroicon: chevron-right, size-4, text-gray-300 -->
</a>
{% endfor %}
```

> Note: Jinja2 doesn't support list literals in `for` loops like this — convert to a Python list passed from the route, or use three separate blocks.

---

## Interactions & Behaviour

| Interaction | Behaviour |
|------------|-----------|
| "Create free account →" (hero + CTA section) | Navigate to `url_for('auth.register')` |
| "Already have an account? Sign in" | Navigate to `url_for('auth.login')` |
| Homepage sign-up form submission | POST to register route (same form as `auth/register.html`) |
| Article prev/next nav | Standard `<a>` link navigation, no JS needed |
| Profile action cards | Standard `<a>` link navigation |
| Mobile filter pills | CSS `overflow-x: auto` horizontal scroll, no JS toggle needed |

---

## Design Tokens

All from Tailwind defaults — no custom theme needed.

| Token | Value | Tailwind class |
|-------|-------|---------------|
| Primary | `#3b82f6` | `blue-500` |
| Primary dark | `#1d4ed8` | `blue-700` |
| Nav / hero bg | `#000000` | `black` |
| Page bg | `#f9fafb` | `gray-50` |
| Card bg | `#ffffff` | `white` |
| Body text | `#374151` | `gray-700` |
| Secondary text | `#6b7280` | `gray-500` |
| Heading text | `#111827` | `gray-900` |
| Muted text | `#9ca3af` | `gray-400` |
| Border | `#d1d5db` | `gray-300` |
| Nav text | `#e2e8f0` | `slate-200` |
| Hero card bg | `#111827` | `gray-900` |
| Hero card border | `#1f2937` | `gray-800` |
| CTA gradient | `linear-gradient(135deg, #1e3a5f, #1d4ed8)` | inline style |

---

## Icons

Use **Heroicons outline** (`viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `stroke-width="1.5"`, `stroke-linecap="round"`, `stroke-linejoin="round"`).

Icons needed:
- **Bookmark** — pillar 1 (Save from anywhere)
- **Clock** — pillar 2 (AI summaries)
- **Magnifying glass** — pillar 3 (Find it)
- **User/Person** — Profile: Edit Profile action
- **Bars** (list) — Profile: Reclassify action
- **Key** — Profile: API Token action
- **Chevron right** — Profile action card trailing icon
- **Arrow left** — Article detail "Back to articles" button (already exists)
- **External link** — Article detail "Read full article" button (already exists)

All available at [heroicons.com](https://heroicons.com) — copy inline SVG.

---

## Files in This Package

| File | Purpose |
|------|---------|
| `Recap Redesign.html` | Full interactive design canvas — open in browser to review all screens |
| `recap-pages/homepage.jsx` | Homepage component source |
| `recap-pages/app-home.jsx` | Authenticated home component source |
| `recap-pages/article-detail.jsx` | Article detail component source |
| `recap-pages/other-pages.jsx` | Profile, Login, Register component sources |
| `recap-pages/nav.jsx` | Shared nav component source |
| `design-system.md` | Full existing design system documentation |
| `vision.md` | Product vision and copy reference |

---

## Implementation Priority

1. **Homepage unauthenticated** — highest value, currently a placeholder
2. **Login & Register pages** — quick wins, same card pattern
3. **Profile page** — remove article list, add action cards
4. **Article detail prev/next** — requires a small route change
5. **Mobile filter pills** — replace toggle with scroll row

---

## Copy Reference

All body copy for the homepage is in `vision.md`. Key phrases:

- Tagline: *"Bookmark it. Recap will remember it."*
- Sub: *"Save any article from the web. Recap summarises it, organises it, and delivers a weekend digest for your morning coffee — all automatically."*
- Privacy: *"Your reading history is private by default."*
- How it works sub: *"Three steps. Zero effort after setup."*
