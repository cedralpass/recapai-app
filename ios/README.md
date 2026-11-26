# Recap iOS app + Safari Share Extension

Save the page you're reading in Safari to Recap: **Share → Recap**. The extension sends the
page URL plus its rendered HTML to `POST /api/v1/articles` (same contract as the Chrome
extension), so blocked/paywalled sites still get summarized from what's on screen.

## Layout

| Path | What |
|------|------|
| `project.yml` | XcodeGen spec — the `.xcodeproj` is generated, not committed |
| `RecapAI/` | Host app: Articles / Digest / Settings tabs (see `docs/ios_share_extension.md`) |
| `RecapShare/` | Share extension (`ShareViewController.swift`) + `GetPage.js` (runs in Safari, returns URL/title/HTML) |
| `Shared/RecapClient.swift` | Settings (App Group `group.com.gsmalling.recapai`) + API client (save + read API), used by both targets |
| `Shared/Models.swift` | Codable models for the read API |

## Build & run

```bash
cd ios
xcodegen generate
xcodebuild -project RecapAI.xcodeproj -scheme RecapAI \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath build build | xcbeautify
```

Or `open RecapAI.xcodeproj` and press Run. Re-run `xcodegen generate` after adding/removing files.

In the app, set the server URL (`http://localhost:8080` for local dev in the simulator) and paste
your token from `/settings/api-token`.

## Running on your iPhone

Set `DEVELOPMENT_TEAM` in `project.yml` (or in Xcode → Signing & Capabilities for both targets),
regenerate, plug in the phone and Run. A free Apple ID works but apps expire after 7 days;
TestFlight/App Store need the paid Developer Program. The bundle IDs / App Group may need to be
made unique (e.g. `com.<you>.recapai`) if Apple says they're taken.

## Notes

- Settings live in the shared App Group `UserDefaults` (token included), mirroring how the
  Chrome extension stores it. Moving the token to a shared Keychain item is a future hardening step.
- HTML over ~4.5 MB is dropped and only the URL is sent (server caps bodies at 5 MB).
- Requests send `X-Recap-Client: ios-share/<version>`, which updates `User.extension_last_seen`.
