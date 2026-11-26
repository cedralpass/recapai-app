# iOS App & Safari Share Extension

Save the article you're reading on iPhone to Recap: in Safari tap **Share → Recap**. The
extension sends the page URL **and its rendered HTML** to the backend, so sites that block our
crawler (Medium, paywalls) still get summarized from what's on screen.

It uses the same token-authenticated API as the Chrome extension (`POST /api/v1/articles`) — no
server changes were needed.

---

## Architecture overview

```
[Safari page]
   │  Share → Recap
   ▼
[RecapShare extension]
   │  GetPage.js runs in the page → { url, title, html }
   │
   │  POST /api/v1/articles
   │  Authorization: Bearer <api_token>
   │  X-Recap-Client: ios-share/<version>
   │  { "url": "https://...", "html": "<!doctype html>..." }
   ▼
[RecapAI Flask app]
   ├─ extract_article_text(html) → Article.content_text (content_source="extension")
   ├─ Article.upsert_for_user() — re-sharing a URL updates instead of duplicating
   └─ Enqueues recap.tasks.classify_url via RQ
```

```
ios/
├── project.yml                 # XcodeGen spec (source of truth; .xcodeproj is generated + gitignored)
├── README.md                   # Quick build/run notes
├── RecapAI/                    # Host app
│   ├── RecapAIApp.swift        # Settings screen: server URL + API token
│   └── Assets.xcassets/        # App icon (1024px "R", same style as the Chrome icons)
├── RecapShare/                 # Share extension
│   ├── ShareViewController.swift  # Reads Safari's JS results, posts, shows status, auto-dismisses
│   └── GetPage.js              # NSExtensionJavaScriptPreprocessingFile — returns URL/title/HTML
└── Shared/
    └── RecapClient.swift       # RecapSettings (App Group storage) + RecapClient (API call)
```

### How the pieces fit

- **Activation:** the extension appears for web pages and URLs
  (`NSExtensionActivationSupportsWebPageWithMaxCount` / `...WebURLWithMaxCount`).
- **Page capture:** Safari runs `GetPage.js` inside the page before the extension opens and hands
  back `NSExtensionJavaScriptPreprocessingResultsKey`. If that's missing (e.g. sharing a link from
  another app), the extension falls back to sending just the URL.
- **Settings sharing:** the host app and extension share settings through the App Group
  `group.com.gsmalling.recapai` (`UserDefaults(suiteName:)`). The token is stored there, mirroring
  how the Chrome extension uses `chrome.storage.sync`.
- **Size cap:** HTML over ~4.5 MB is dropped and only the URL is sent (server rejects bodies > 5 MB).
- **Responses** map to the same messages as the Chrome extension: 201 → "Saved!", 200 `updated` →
  "Updated with full text", 200 `exists` → "Already in your Recap list", 401 → "Invalid API token".
- **Client header:** `X-Recap-Client: ios-share/<version>` updates `User.extension_last_seen`.

---

## Prerequisites (one-time)

- **Xcode 26+** from the Mac App Store; then
  `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer` and
  `sudo xcodebuild -license accept`
- **iOS Simulator runtime** — Xcode → Settings → Components (≈8.5 GB)
- `brew install xcodegen xcbeautify`

---

## Build & run in the simulator

```bash
cd ios
xcodegen generate
xcodebuild -project RecapAI.xcodeproj -scheme RecapAI \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath build build | xcbeautify
```

Then install/launch the `.app` from `build/Build/Products/Debug-iphonesimulator/` (or just
`open RecapAI.xcodeproj` and press Run).

For local testing, run the `recap` dev server and set the app's server URL to
`http://localhost:8080` — the simulator shares the Mac's localhost, and the Info.plist allows
local networking (`NSAllowsLocalNetworking`). Paste a token from `/settings/api-token`.

Re-run `xcodegen generate` whenever you add or remove source files.

---

## Install on an iPhone

One-time setup:

1. Xcode → Settings → Accounts → **+** → Apple Account (a free Apple ID gives a "Personal Team").
2. Plug in the iPhone, unlock it, tap **Trust This Computer**.
3. Enable **Settings → Privacy & Security → Developer Mode** on the phone. The switch only appears
   after Xcode has tried to install something — if it's missing, attempt an install first.
4. `DEVELOPMENT_TEAM` in `ios/project.yml` must be your team ID (find it in
   `~/Library/Preferences/com.apple.dt.Xcode.plist` under `IDEProvisioningTeamByIdentifier`, or
   Xcode → target → Signing & Capabilities).

Build, sign and install:

```bash
cd ios
xcodebuild -project RecapAI.xcodeproj -scheme RecapAI -destination 'generic/platform=iOS' \
  -derivedDataPath build -allowProvisioningUpdates build | xcbeautify
xcrun devicectl list devices                      # get the device identifier
xcrun devicectl device install app --device <device-id> \
  build/Build/Products/Debug-iphoneos/RecapAI.app
```

The first signing run prompts for the Mac **login keychain password** (`codesign` wants the new
"Apple Development" certificate) — choose **Always Allow**.

In the app on the phone: keep the server URL as `https://dev.recaprai.com` (or your server), paste
your API token, tap **Save**. In Safari, if Recap isn't in the share sheet's app row, tap
**More → Edit** and enable it.

### Gotchas

- **Free signing expires after 7 days** — rebuild and reinstall. TestFlight/App Store need the
  paid Apple Developer Program.
- **Bundle IDs must be globally unique** — they're `com.gsmalling.recapai` /
  `com.gsmalling.recapai.share` with App Group `group.com.gsmalling.recapai`. If you change them,
  update `RecapSettings.appGroup` in `Shared/RecapClient.swift` to match.
- **"Timed out waiting for destinations"** from `xcodebuild` usually means the phone isn't ready for
  development (Developer Mode off / device shows "no DDI"). Build with
  `-destination 'generic/platform=iOS'` and install with `devicectl` instead.

---

## Future work

- Move the API token from App Group `UserDefaults` into a shared Keychain item
- Proper app icon / branding
- Show recent saves (and classification status) in the host app
- TestFlight distribution (needs paid Developer Program)
