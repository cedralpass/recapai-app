import SwiftUI

@MainActor
@Observable
final class DigestModel {
    enum State {
        case loading
        case none(articlesSinceLast: Int)
        case loaded(Digest)
        case failed(String)
    }

    static let pollInterval: Duration = .seconds(3)
    static let maxPolls = 60  // ~3 minutes

    private(set) var state: State = .loading
    private(set) var isGenerating = false
    var generateError: String?

    private var client: RecapClient { RecapClient() }

    /// Fetches the latest digest; this marks it opened on the server (clears the web/app dot).
    func load() async {
        if case .loaded = state {} else { state = .loading }
        do {
            switch try await client.latestDigest(markOpened: true) {
            case .digest(let digest): state = .loaded(digest)
            case .none(let count): state = .none(articlesSinceLast: count)
            }
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    /// Queue a digest, poll the job until it finishes, then reload.
    func generate() async {
        guard !isGenerating else { return }
        isGenerating = true
        generateError = nil
        defer { isGenerating = false }
        do {
            let jobID = try await client.generateDigest()
            for _ in 0..<Self.maxPolls {
                try await Task.sleep(for: Self.pollInterval)
                let status = try await client.digestJobStatus(jobID)
                if status.isFinished {
                    await load()
                    if case .none = state {
                        generateError = "Not enough new articles for a digest yet."
                    }
                    return
                }
                if status.isFailed {
                    generateError = "Digest generation failed. Try again in a moment."
                    return
                }
            }
            generateError = "Still generating — check back in a few minutes."
        } catch is CancellationError {
            return
        } catch {
            generateError = error.localizedDescription
        }
    }
}

struct DigestView: View {
    @Environment(AppModel.self) private var app
    @State private var model = DigestModel()
    @State private var path = NavigationPath()
    @State private var safari: SafariDestination?
    @State private var webHeight: CGFloat = 400

    var body: some View {
        NavigationStack(path: $path) {
            Group {
                if !app.isConfigured {
                    ConnectRecapView()
                } else {
                    content
                }
            }
            .background(Theme.paper)
            .navigationTitle("Digest")
            .navigationDestination(for: ArticleRoute.self) { route in
                ArticleDetailView(articleID: route.id)
            }
        }
        .safariCover($safari)
        .task(id: TaskKey(version: app.settingsVersion, tab: app.selectedTab)) {
            guard app.isConfigured, app.selectedTab == .digest else { return }
            await model.load()
            app.hasUnreadDigest = false
        }
    }

    private struct TaskKey: Equatable {
        let version: Int
        let tab: AppTab
    }

    @ViewBuilder
    private var content: some View {
        switch model.state {
        case .loading:
            ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
        case .failed(let message):
            ContentUnavailableView {
                Label("Couldn't load your digest", systemImage: "exclamationmark.triangle")
            } description: {
                Text(message)
            } actions: {
                Button("Retry") { Task { await model.load() } }
            }
        case .none(let count):
            emptyState(articlesSinceLast: count)
        case .loaded(let digest):
            digestScroll(digest)
        }
    }

    private func digestScroll(_ digest: Digest) -> some View {
        ScrollView {
            VStack(spacing: 12) {
                if digest.showRegenerate || model.isGenerating || model.generateError != nil {
                    regenerateBanner(digest)
                }
                digestCard(digest)
            }
            .padding(.horizontal, 16)
            .padding(.top, 4)
            .padding(.bottom, 24)
        }
        .refreshable { await model.load() }
    }

    private func regenerateBanner(_ digest: Digest) -> some View {
        NoticeCard {
            HStack(spacing: 10) {
                Group {
                    if model.isGenerating {
                        Text("Generating a fresh digest…")
                    } else if let error = model.generateError {
                        Text(error)
                    } else {
                        Text("**\(digest.bookmarksSince) new bookmark\(digest.bookmarksSince == 1 ? "" : "s")** since this digest.")
                    }
                }
                .font(.system(size: 14))
                .foregroundStyle(Theme.noticeBody)
                .frame(maxWidth: .infinity, alignment: .leading)

                Button {
                    Task { await model.generate() }
                } label: {
                    HStack(spacing: 6) {
                        if model.isGenerating {
                            ProgressView().tint(.white).controlSize(.small)
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                        Text(model.isGenerating ? "Generating…" : "Regenerate")
                    }
                    .font(.system(size: 13, weight: .bold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 11)
                    .padding(.vertical, 7)
                    .background(Theme.ink, in: RoundedRectangle(cornerRadius: 8))
                }
                .buttonStyle(.plain)
                .disabled(model.isGenerating)
            }
        }
    }

    private func digestCard(_ digest: Digest) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Recap · Week of \(digest.weekStartLabel ?? "this week")")
                    .font(.system(size: 10, weight: .bold))
                    .kerning(1.6)
                    .textCase(.uppercase)
                    .foregroundStyle(Theme.amber)
                Text("Your Weekly Recap")
                    .font(.system(size: 26, weight: .bold, design: .serif))
                    .foregroundStyle(Theme.ink)
                Text(metaLine(digest))
                    .font(.system(size: 14))
                    .foregroundStyle(Color(hex: 0x64748B))
            }
            .padding(EdgeInsets(top: 20, leading: 20, bottom: 16, trailing: 20))
            .frame(maxWidth: .infinity, alignment: .leading)

            Divider().overlay(Color(hex: 0xF1F5F9))

            if let html = digest.digestHtml, !html.isEmpty {
                DigestWebView(html: html, height: $webHeight, onLink: open)
                    .frame(height: webHeight)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 14)
            } else {
                Text("This digest has no content.")
                    .foregroundStyle(Theme.secondary)
                    .padding(20)
            }
        }
        .background(.white, in: RoundedRectangle(cornerRadius: 16))
        .shadow(color: .black.opacity(0.06), radius: 1.5, y: 1)
    }

    private func metaLine(_ digest: Digest) -> String {
        var parts: [String] = []
        if let n = digest.articleCount { parts.append("\(n) article\(n == 1 ? "" : "s")") }
        if let k = digest.clusterCount, k > 0 { parts.append("\(k) topic\(k == 1 ? "" : "s")") }
        return parts.joined(separator: " · ")
    }

    private func emptyState(articlesSinceLast count: Int) -> some View {
        ScrollView {
            VStack(spacing: 0) {
                Image(systemName: "sparkles")
                    .font(.system(size: 32))
                    .foregroundStyle(Theme.amber)
                    .frame(width: 72, height: 72)
                    .background(Theme.noticeBackground, in: RoundedRectangle(cornerRadius: 20))
                    .padding(.bottom, 20)
                Text("No digest yet this week")
                    .font(.system(size: 24, weight: .bold, design: .serif))
                    .foregroundStyle(Theme.ink)
                    .padding(.bottom, 8)
                Text("You've saved **\(count) article\(count == 1 ? "" : "s")** since your last recap. Recap can group them into themes and pull out what matters.")
                    .font(.system(size: 16))
                    .foregroundStyle(Theme.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.bottom, 26)

                Button {
                    Task { await model.generate() }
                } label: {
                    HStack(spacing: 8) {
                        if model.isGenerating { ProgressView().tint(.white) }
                        Text(model.isGenerating ? "Generating…" : "Generate digest")
                    }
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(.white)
                    .frame(width: 240, height: 50)
                    .background(Theme.ink, in: RoundedRectangle(cornerRadius: 14))
                }
                .buttonStyle(.plain)
                .disabled(model.isGenerating)
                .padding(.bottom, 14)

                if let error = model.generateError {
                    Text(error)
                        .font(.system(size: 13))
                        .foregroundStyle(Theme.noticeText)
                        .multilineTextAlignment(.center)
                } else {
                    Text("Takes about a minute · it will appear here")
                        .font(.system(size: 13))
                        .foregroundStyle(Theme.tertiary)
                }
            }
            .padding(.horizontal, 40)
            .padding(.top, 100)
            .frame(maxWidth: .infinity)
        }
        .refreshable { await model.load() }
    }

    /// Recap article links ("/<id>/show") open in-app detail; everything else in Safari view.
    private func open(_ url: URL) {
        let parts = url.path.split(separator: "/")
        if parts.count == 2, parts[1] == "show", let id = Int(parts[0]) {
            path.append(ArticleRoute(id: id))
        } else if let url = safariURL(url) {
            safari = SafariDestination(url: url)
        }
    }
}
