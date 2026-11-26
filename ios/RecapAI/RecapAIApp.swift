import SwiftUI

@main
struct RecapAIApp: App {
    @State private var app = AppModel()
    @State private var articles = ArticlesModel()
    @Environment(\.scenePhase) private var scenePhase

    init() {
        // Amber dot for the Digest tab badge (mirrors the web nav indicator).
        let item = UITabBarItemAppearance()
        item.normal.badgeBackgroundColor = UIColor(Theme.amber)
        item.selected.badgeBackgroundColor = UIColor(Theme.amber)
        let appearance = UITabBarAppearance()
        appearance.configureWithDefaultBackground()
        appearance.stackedLayoutAppearance = item
        appearance.inlineLayoutAppearance = item
        appearance.compactInlineLayoutAppearance = item
        UITabBar.appearance().standardAppearance = appearance
        UITabBar.appearance().scrollEdgeAppearance = appearance
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(app)
                .environment(articles)
                .tint(Theme.tint)
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active {
                Task { await app.refreshDigestBadge() }
            }
        }
    }
}

enum AppTab: Hashable {
    case articles, digest, settings
}

/// App-wide state: selected tab, whether Recap is configured, unread-digest dot.
@MainActor
@Observable
final class AppModel {
    var selectedTab: AppTab = .articles
    var isConfigured = RecapSettings.isConfigured
    var hasUnreadDigest = false
    /// Bumped when the server URL / token change so tabs reload.
    var settingsVersion = 0

    func settingsChanged() {
        isConfigured = RecapSettings.isConfigured
        settingsVersion += 1
        Task { await refreshDigestBadge() }
    }

    func refreshDigestBadge() async {
        guard RecapSettings.isConfigured else {
            hasUnreadDigest = false
            return
        }
        // Don't clear the badge while the user is looking at the digest.
        guard selectedTab != .digest else { return }
        if case .digest(let digest) = try? await RecapClient().latestDigest(markOpened: false) {
            hasUnreadDigest = digest.wasUnread
        } else {
            hasUnreadDigest = false
        }
    }
}

struct RootView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        @Bindable var app = app
        TabView(selection: $app.selectedTab) {
            ArticlesView()
                .tabItem { Label("Articles", systemImage: "list.bullet") }
                .tag(AppTab.articles)

            DigestView()
                .tabItem { Label("Digest", systemImage: "newspaper") }
                .tag(AppTab.digest)
                .badge(app.hasUnreadDigest ? Text(" ") : nil)

            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
                .tag(AppTab.settings)
        }
        .task { await app.refreshDigestBadge() }
    }
}
