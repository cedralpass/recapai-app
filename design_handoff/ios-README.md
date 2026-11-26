# Handoff: Recap iOS App — Articles, Detail, Digest

Design references for the native iOS app (`ios/`, SwiftUI). Open **`Recap iOS.html`** (same
design-canvas format as `Recap Redesign.html`; serve the folder over HTTP, e.g. the `design`
launch config on port 8091). Screen components live in `recap-ios/ios-screens.jsx`.

Feature plan and API contract: **[docs/ios_app_ux_plan.md](../docs/ios_app_ux_plan.md)**.

---

## Fidelity & approach

**Mid-to-high fidelity.** Layout, hierarchy, copy and colours are final; exact metrics should come
from native SwiftUI defaults. These are **not** pixel specs to fight the platform with — use
`NavigationStack`, `List`/`ScrollView`, `.searchable`, `TabView`, large titles and SF Symbols, and
apply the Recap tokens below on top.

Frame: iPhone 17 Pro, 402 × 874 pt.

## Tokens

| Token | Value | Use |
|-------|-------|-----|
| Tint | `#3b82f6` (Tailwind blue-500) | App accent: tab selection, links, primary buttons, unread dot, active filter pill |
| Background | `systemGroupedBackground` (`#f2f2f7`) | Articles, Settings |
| Card | white, 14 pt radius, no shadow | Article cards |
| Category badge | `#f3f4f6` bg, `#374151` text, 12 pt semibold, capsule | Same as web badge |
| Digest paper | `#fafaf9` bg (stone-50), white card 16 pt radius | Digest tab |
| Digest eyebrow | `#d97706` (amber-600), 10 pt bold, 0.16em tracking, uppercase | "Recap · Week of …" |
| Digest headings | Serif (New York / `.serif` design) bold | Matches web/email digest |
| Notice | `#fffbeb` bg, `#fcd34d` border, `#92400e` text | "Summary not available", regenerate banner |
| Brand mark | Black rounded square, white "R" | Articles nav bar trailing item, app icon |

## Navigation

`TabView` with three tabs: **Articles** (`list.bullet`), **Digest** (`newspaper`), **Settings**
(`gearshape`). The Digest tab shows an amber dot badge when there's an unread digest (mirrors the
web nav indicator).

---

## Screens

### iOS 01 · Articles (home)

- Large title "Articles"; black "R" brand mark trailing.
- `.searchable` field, placeholder "Search your articles". Search is **semantic** (same as web
  `/search`) — submit on return, not per keystroke. Results header "N RESULTS FOR “q”"; matched
  terms highlighted (yellow-200) where they appear literally.
- Horizontal category pill row (scrolls): "All" + user categories with counts, sorted by count.
  Active pill = tint fill, white text; inactive = white with hairline border.
- Section label "RECENTLY SAVED"; cards newest first, infinite scroll (pages of 20).
- **Card:** title (16 semibold, 2 lines), date trailing (13, tertiary), summary (14, 2-line
  clamp), bottom row = category badge + source domain. Unread = 7 pt tint dot at leading edge and
  full-strength title; read titles are slightly muted.
- URL-only articles (site blocked us) replace the summary with an amber
  "⚠ Summary not available — tap to read" line.
- Swipe actions: leading = Mark read/unread; trailing = Delete (confirm).
- Pull to refresh. Empty state: "Nothing saved yet — use Share → Recap in Safari."

### iOS 02 · Article detail

- Standard back button "Articles"; trailing toolbar: read/unread toggle, system share.
- Category badge + "Saved {date}", title (28 bold), "{author} · {domain}" (author hidden if
  Unknown/Not specified).
- "SUMMARY" section label, summary body 17 pt / 1.55 line height.
- "KEY TOPICS" bullet list (tint dots).
- **Sticky bottom CTA**: full-width tint button "Read article" with Safari glyph, caption
  "Opens in Safari view · marks as read". Opens `SFSafariViewController` and marks the article read.
- **Variant — summary not available:** amber notice card replaces Summary/Topics: "This site
  blocked Recap from reading it… Open it in Safari and tap **Share → Recap** to send the full text."

### iOS 03 · Digest

- Large title "Digest" on stone-50.
- **Regenerate banner** (only when ≥ `DIGEST_REGENERATE_THRESHOLD` new bookmarks): amber notice
  "**N new bookmarks** since this digest." + dark "Regenerate" button.
- **Digest card**: eyebrow "Recap · Week of {Month D}", serif "Your Weekly Recap", meta
  "{n} articles · {k} topics", then the digest body.
- Body = the server's `digest_html` rendered in a `WKWebView` with a small injected stylesheet
  (system font for body, serif for headings, tint links). Article links inside open the in-app
  article detail when they point at Recap, otherwise Safari view.
- **Empty state**: sparkle tile, serif "No digest yet this week", "You've saved **N articles**
  since your last recap…", dark "Generate digest" button, caption "Takes about a minute · it will
  appear here". While generating: button becomes a spinner + "Generating…", poll job status.
- Opening the tab marks the digest opened (clears the tab dot), same as web `opened_at`.

### iOS 04 · Settings & share (exists — restyle only)

- Settings moves into its own tab. Groups: **Account** (server, token with Show), **Share
  extension** (connection status from last successful save; "How to add Recap to the share
  sheet"), **More** ("Open Recap on the web").
- Share confirmation sheet is unchanged from what shipped.
