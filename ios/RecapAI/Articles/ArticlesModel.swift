import Foundation

/// Articles tab state, shared with detail views (opened from the list or the digest)
/// so read/delete changes show up everywhere.
@MainActor
@Observable
final class ArticlesModel {
    static let pageSize = 20

    private(set) var articles: [Article] = []
    private(set) var categories: [CategoryCount] = []
    private(set) var totalCount = 0
    var selectedCategory: String?
    private(set) var hasNext = false
    private(set) var isLoading = false
    private(set) var hasLoaded = false
    var errorMessage: String?

    /// Submitted search (nil = browsing the list).
    private(set) var searchQuery: String?
    private(set) var searchResults: [Article] = []
    private(set) var isSearching = false

    private var page = 1
    private var loadedVersion = -1

    private var client: RecapClient { RecapClient() }

    /// Load once per settings version (token/server change triggers a reload).
    func loadIfNeeded(settingsVersion: Int) async {
        guard loadedVersion != settingsVersion else { return }
        loadedVersion = settingsVersion
        articles = []
        hasLoaded = false
        searchQuery = nil
        await refresh()
    }

    func refresh() async {
        async let cats: Void = loadCategories()
        await loadFirstPage()
        await cats
        if let searchQuery { await search(searchQuery) }
    }

    func selectCategory(_ category: String?) async {
        guard category != selectedCategory else { return }
        selectedCategory = category
        if let searchQuery {
            await search(searchQuery)
        } else {
            await loadFirstPage()
        }
    }

    func loadFirstPage() async {
        isLoading = true
        defer { isLoading = false }
        do {
            let result = try await client.listArticles(page: 1, perPage: Self.pageSize, category: selectedCategory)
            articles = result.articles
            hasNext = result.hasNext
            page = 1
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
        hasLoaded = true
    }

    /// Infinite scroll: called when the last row appears.
    func loadMoreIfNeeded(current article: Article) async {
        guard hasNext, !isLoading, article.id == articles.last?.id else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            let result = try await client.listArticles(page: page + 1, perPage: Self.pageSize, category: selectedCategory)
            let known = Set(articles.map(\.id))
            articles.append(contentsOf: result.articles.filter { !known.contains($0.id) })
            hasNext = result.hasNext
            page += 1
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func loadCategories() async {
        if let cats = try? await client.categories() {
            categories = cats
            totalCount = cats.reduce(0) { $0 + $1.count }
        }
    }

    // MARK: Search

    func search(_ q: String) async {
        let q = q.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { clearSearch(); return }
        searchQuery = q
        isSearching = true
        defer { isSearching = false }
        do {
            searchResults = try await client.searchArticles(q, category: selectedCategory)
            errorMessage = nil
        } catch {
            searchResults = []
            errorMessage = error.localizedDescription
        }
    }

    func clearSearch() {
        searchQuery = nil
        searchResults = []
    }

    // MARK: Mutations

    func article(id: Int) -> Article? {
        articles.first { $0.id == id } ?? searchResults.first { $0.id == id }
    }

    /// Optimistically set read state, then sync with the server's copy.
    @discardableResult
    func setRead(_ read: Bool, for article: Article) async -> Article {
        var optimistic = article
        optimistic.read = read
        apply(optimistic)
        do {
            let updated = try await client.setRead(read, articleID: article.id)
            apply(updated)
            return updated
        } catch {
            apply(article)
            errorMessage = error.localizedDescription
            return article
        }
    }

    func delete(_ article: Article) async {
        let previousArticles = articles
        let previousResults = searchResults
        articles.removeAll { $0.id == article.id }
        searchResults.removeAll { $0.id == article.id }
        do {
            try await client.deleteArticle(id: article.id)
            await loadCategories()
        } catch RecapError.notFound {
            await loadCategories()
        } catch {
            articles = previousArticles
            searchResults = previousResults
            errorMessage = error.localizedDescription
        }
    }

    func apply(_ updated: Article) {
        if let i = articles.firstIndex(where: { $0.id == updated.id }) { articles[i] = updated }
        if let i = searchResults.firstIndex(where: { $0.id == updated.id }) { searchResults[i] = updated }
    }
}
