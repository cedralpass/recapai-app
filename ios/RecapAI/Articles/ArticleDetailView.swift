import SwiftUI

struct ArticleDetailView: View {
    let articleID: Int

    @Environment(ArticlesModel.self) private var model
    @State private var loaded: Article?
    @State private var errorMessage: String?
    @State private var safari: SafariDestination?

    /// Prefer the shared store's copy so read-state changes from the list show here too.
    private var article: Article? { model.article(id: articleID) ?? loaded }

    var body: some View {
        Group {
            if let article {
                content(article)
            } else if let errorMessage {
                ContentUnavailableView {
                    Label("Couldn't load article", systemImage: "exclamationmark.triangle")
                } description: {
                    Text(errorMessage)
                } actions: {
                    Button("Retry") { Task { await load() } }
                }
            } else {
                ProgressView()
            }
        }
        .background(.white)
        .navigationBarTitleDisplayMode(.inline)
        .task { if model.article(id: articleID) == nil { await load() } }
        .safariCover($safari)
    }

    private func load() async {
        errorMessage = nil
        do {
            loaded = try await RecapClient().article(id: articleID)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func content(_ article: Article) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                HStack(spacing: 8) {
                    if let category = article.category { CategoryBadge(name: category) }
                    if let created = article.created {
                        Text("Saved \(created.shortLabel)")
                            .font(.system(size: 13))
                            .foregroundStyle(Theme.tertiary)
                    }
                }
                .padding(.bottom, 12)

                Text(article.displayTitle)
                    .font(.system(size: 28, weight: .bold))
                    .foregroundStyle(Theme.label)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.bottom, 10)

                Text([article.displayAuthor, article.source].compactMap { $0 }.joined(separator: " · "))
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.secondary)
                    .padding(.bottom, 20)

                if article.summaryAvailable, let summary = article.summary {
                    sectionLabel("Summary")
                    Text(summary)
                        .font(.system(size: 17))
                        .lineSpacing(17 * 0.55 - 4)
                        .foregroundStyle(Color(hex: 0x1F2937))
                        .padding(.bottom, 22)

                    if !article.keyTopics.isEmpty {
                        sectionLabel("Key topics")
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(article.keyTopics, id: \.self) { topic in
                                HStack(alignment: .firstTextBaseline, spacing: 10) {
                                    Circle().fill(Theme.tint).frame(width: 6, height: 6)
                                        .alignmentGuide(.firstTextBaseline) { $0[.bottom] + 2 }
                                    Text(topic).font(.system(size: 16)).foregroundStyle(Theme.badgeText)
                                }
                            }
                        }
                    }
                } else {
                    NoticeCard {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Summary not available", systemImage: "exclamationmark.triangle")
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundStyle(Theme.noticeText)
                            Text("This site blocked Recap from reading it, so the category is a guess from the link. Open it in Safari and tap **Share → Recap** to send the full text.")
                                .font(.system(size: 14))
                                .foregroundStyle(Theme.noticeBody)
                        }
                    }
                }
            }
            .padding(.horizontal, 22)
            .padding(.top, 10)
            .padding(.bottom, 24)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .safeAreaInset(edge: .bottom) { readButton(article) }
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button {
                    Task { await toggleRead(article) }
                } label: {
                    Image(systemName: article.read ? "circle" : "largecircle.fill.circle")
                }
                .accessibilityLabel(article.read ? "Mark unread" : "Mark read")

                if let url = article.webURL {
                    ShareLink(item: url)
                }
            }
        }
    }

    private func readButton(_ article: Article) -> some View {
        VStack(spacing: 8) {
            Button {
                openArticle(article)
            } label: {
                Label("Read article", systemImage: "safari")
                    .font(.system(size: 17, weight: .semibold))
                    .frame(maxWidth: .infinity, minHeight: 52)
                    .foregroundStyle(.white)
                    .background(Theme.tint, in: RoundedRectangle(cornerRadius: 14))
            }
            .disabled(safariURL(article.webURL) == nil)
            Text("Opens in Safari view · marks as read")
                .font(.system(size: 12))
                .foregroundStyle(Theme.tertiary)
        }
        .padding(.horizontal, 20)
        .padding(.top, 14)
        .padding(.bottom, 8)
        .background(
            LinearGradient(stops: [.init(color: .white.opacity(0), location: 0), .init(color: .white, location: 0.3)],
                           startPoint: .top, endPoint: .bottom)
        )
    }

    private func openArticle(_ article: Article) {
        guard let url = safariURL(article.webURL) else { return }
        safari = SafariDestination(url: url)
        if !article.read {
            Task { await setRead(true, article) }
        }
    }

    private func toggleRead(_ article: Article) async {
        await setRead(!article.read, article)
    }

    private func setRead(_ read: Bool, _ article: Article) async {
        if loaded != nil { loaded?.read = read }
        let updated = await model.setRead(read, for: article)
        if loaded != nil { loaded = updated }
    }

    private func sectionLabel(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 13, weight: .semibold))
            .textCase(.uppercase)
            .kerning(0.5)
            .foregroundStyle(Theme.secondary)
            .padding(.bottom, 8)
    }
}
