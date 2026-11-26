# iOS Build & Install

Step-by-step runbook for building the Recap iOS app (app + Safari Share Extension) and getting it
onto the Simulator or an iPhone. For what the app does and how it's put together, see
[ios_share_extension.md](ios_share_extension.md).

All commands run from the repo root unless noted. The Xcode project is **generated** from
`ios/project.yml` by XcodeGen and is gitignored, so always regenerate before building.

---

## One-time setup

1. **Xcode 26+** from the Mac App Store, then:
   ```bash
   sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
   ```
   ```bash
   sudo xcodebuild -license accept
   ```
2. **iOS Simulator runtime**: Xcode → Settings → Components (about 8.5 GB).
3. **Tools**:
   ```bash
   brew install xcodegen xcbeautify
   ```
4. **For a real iPhone only**:
   - Xcode → Settings → Accounts → **+** → Apple Account (a free Apple ID gives a "Personal Team").
   - Plug in the iPhone, unlock it, tap **Trust This Computer**.
   - On the phone: **Settings → Privacy & Security → Developer Mode** → On (the switch appears only
     after Xcode has tried an install once; restart when asked).
   - `DEVELOPMENT_TEAM` in `ios/project.yml` must be your team ID (Xcode → target → Signing &
     Capabilities shows it).

---

## Install on your iPhone

Plug in the phone and unlock it.

**1. Generate the project and build a signed device build**

```bash
cd ios && xcodegen generate && xcodebuild -project RecapAI.xcodeproj -scheme RecapAI -destination 'generic/platform=iOS' -derivedDataPath build -allowProvisioningUpdates build | xcbeautify
```

Ends with `Build Succeeded`. The first signing run may ask for your Mac **login keychain
password**; choose **Always Allow**. The warning "All interface orientations must be supported…" is
expected (the app is portrait-only) and harmless.

**2. Find the phone's device identifier**

```bash
xcrun devicectl list devices
```

Copy the `Identifier` column for your phone (State should be `connected`). It doesn't change, so
you only need to look it up once.

**3. Install**

```bash
xcrun devicectl device install app --device <device-id> ios/build/Build/Products/Debug-iphoneos/RecapAI.app
```

Ends with `App installed: • bundleID: com.gsmalling.recapai`. Reinstalling replaces the app and
keeps its settings (server URL + token live in the App Group).

**4. First launch only**

Open **Recap** → **Settings** tab: server `https://dev.recaprai.com`, paste your token from
`/settings/api-token` on the web, tap **Save**. In Safari, if Recap isn't in the share sheet's app
row, scroll to the end → **More** → **Edit** and add it to Favorites.

**Alternative (Xcode UI):** `open ios/RecapAI.xcodeproj` (after `xcodegen generate`), pick your
iPhone as the run destination, press **⌘R**.

### Refreshing every 7 days

Apps signed with a free Apple ID stop launching after **7 days**. Re-run steps 1 and 3 to refresh.
Your settings survive the reinstall. (TestFlight / App Store need the paid Apple Developer Program.)

---

## Run in the Simulator

```bash
cd ios && xcodegen generate && xcodebuild -project RecapAI.xcodeproj -scheme RecapAI -destination 'platform=iOS Simulator,name=iPhone 17 Pro' -derivedDataPath build build | xcbeautify
```

```bash
xcrun simctl boot "iPhone 17 Pro"; open -a Simulator
```

```bash
xcrun simctl install booted ios/build/Build/Products/Debug-iphonesimulator/RecapAI.app && xcrun simctl launch booted com.gsmalling.recapai
```

To test against your local backend:

1. Start the `recap` dev server (port 8080) and, for search, `aiapi` (port 8082); see
   [CLAUDE.md](../CLAUDE.md) → Dev Servers.
2. In the app's **Settings**: server `http://localhost:8080` (the Simulator shares the Mac's
   localhost; local networking is allowed in Info.plist) and a token for a local user from
   `http://localhost:8080/settings/api-token`.
3. Seed data if needed: `.venv/bin/python scripts/load_test_articles.py`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Timed out waiting for destinations` | The phone isn't ready for development: unlock it, check Developer Mode is on. Building with `-destination 'generic/platform=iOS'` + installing with `devicectl` (as above) avoids this. |
| New Swift file "cannot find X in scope" | Run `xcodegen generate`; the project only knows files that existed when it was generated. |
| Signing error / no team | Set `DEVELOPMENT_TEAM` in `ios/project.yml` (or sign in to your Apple account in Xcode → Settings → Accounts) and rebuild with `-allowProvisioningUpdates`. |
| "Bundle ID / App Group not available" | IDs must be globally unique. If you change `com.gsmalling.recapai` / `group.com.gsmalling.recapai` in `project.yml`, also update `RecapSettings.appGroup` in `ios/Shared/RecapClient.swift`. |
| App won't open ("no longer available") | Free signing expired; see Refreshing every 7 days. |
| Articles/Digest show "Connect Recap" | No token saved; set it in the Settings tab. |
| "Invalid API token" | Token was regenerated on the web; paste the new one from `/settings/api-token`. |
| Search always returns no results | The server's embedding call is failing (locally: `aiapi` isn't running). |
