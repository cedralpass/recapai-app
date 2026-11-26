import SwiftUI

/// Identifies an article to open in detail (navigation value).
struct ArticleRoute: Hashable {
    let id: Int
}

struct ArticlesView: View {
    @Environment(AppModel.self) private var app
    @Environment(ArticlesModel.self) private var model
    @State private var searchText = ""
    @State private var searchPresented = false
    @State private var path = NavigationPath()
    @State private var pendingDelete: Article?

    var body: some View {
        NavigationStack(path: $path) {
            Group {
                if !app.isConfigured {
                    ConnectRecapView()
                } else {
                    list
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Articles")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) { BrandMark() }
            }
            .navigationDestination(for: ArticleRoute.self) { route in
                ArticleDetailView(articleID: route.id)
            }
        }
        .task(id: app.settingsVersion) {
            guard app.isConfigured else { return }
            await model.loadIfNeeded(settingsVersion: app.settingsVersion)
        }
    }

    private var list: some View {
        List {
            if model.searchQuery == nil {
                categoryPills
                    .listRowInsets(EdgeInsets())
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
            }

            if let error = model.errorMessage {
                errorRow(error)
            }

            sectionHeader
                .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 0, trailing: 16))
                .listRowBackground(Color.clear)
                .listRowSeparator(.hidden)

            Group {
                ForEach(visibleArticles) { article in
                    Button {
                        path.append(ArticleRoute(id: article.id))
                    } label: {
                        ArticleRow(article: article, query: model.searchQuery ?? "")
                    }
                    .buttonStyle(.plain)
                    .listRowInsets(EdgeInsets(top: 5, leading: 16, bottom: 5, trailing: 16))
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
                    .swipeActions(edge: .leading) {
                        Button {
                            Task { await model.setRead(!article.read, for: article) }
                        } label: {
                            Label(article.read ? "Mark unread" : "Mark read",
                                  systemImage: article.read ? "circle.fill" : "checkmark.circle")
                        }
                        .tint(Theme.tint)
                    }
                    .swipeActions(edge: .trailing) {
                        Button(role: .destructive) {
                            pendingDelete = article
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                        .tint(.red)
                    }
                    .task {
                        if model.searchQuery == nil { await model.loadMoreIfNeeded(current: article) }
                    }
                }

                if model.searchQuery == nil, model.hasNext {
                    HStack { Spacer(); ProgressView(); Spacer() }
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                }
            }

            if showEmptyState {
                emptyState
                    .listRowBackground(Color.clear)
                    .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .searchable(text: $searchText, isPresented: $searchPresented, prompt: "Search your articles")
        .textInputAutocapitalization(.never)
        .onSubmit(of: .search) {
            Task { await model.search(searchText) }
        }
        .onChange(of: searchText) { _, newValue in
            if newValue.isEmpty { model.clearSearch() }
        }
        .onChange(of: searchPresented) { _, presented in
            if !presented { model.clearSearch() }
        }
        .refreshable { await model.refresh() }
        .overlay {
            if !model.hasLoaded || model.isSearching {
                ProgressView()
            }
        }
        .alert(
            "Delete this article?",
            isPresented: Binding(get: { pendingDelete != nil }, set: { if !$0 { pendingDelete = nil } }),
            presenting: pendingDelete
        ) { article in
            Button("Delete", role: .destructive) {
                Task { await model.delete(article) }
            }
            Button("Cancel", role: .cancel) {}
        } message: { article in
            Text(article.displayTitle)
        }
    }

    private var visibleArticles: [Article] {
        model.searchQuery == nil ? model.articles : model.searchResults
    }

    private var showEmptyState: Bool {
        model.hasLoaded && !model.isSearching && visibleArticles.isEmpty && model.errorMessage == nil
    }

    private var sectionHeader: some View {
        Group {
            if let q = model.searchQuery {
                if !model.isSearching {
                    Text("\(model.searchResults.count) results for “\(q)”")
                }
            } else if !model.articles.isEmpty {
                Text("Recently saved")
            }
        }
        .font(.system(size: 13))
        .textCase(.uppercase)
        .foregroundStyle(Theme.secondary)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 4)
    }

    private var categoryPills: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                pill("All", count: model.totalCount > 0 ? model.totalCount : nil, category: nil)
                ForEach(model.categories) { category in
                    pill(category.name, count: category.count, category: category.name)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 4)
        }
    }

    private func pill(_ label: String, count: Int?, category: String?) -> some View {
        let active = model.selectedCategory == category
        return Button {
            Task { await model.selectCategory(category) }
        } label: {
            HStack(spacing: 5) {
                Text(label)
                if let count {
                    Text("\(count)").fontWeight(.medium).opacity(0.6)
                }
            }
            .font(.system(size: 14, weight: .semibold))
            .foregroundStyle(active ? .white : Theme.badgeText)
            .padding(.horizontal, 14)
            .padding(.vertical, 7)
            .background(active ? Theme.tint : .white, in: Capsule())
            .overlay(Capsule().strokeBorder(active ? .clear : Color(hex: 0xD1D5DB), lineWidth: 0.5))
        }
        .buttonStyle(.plain)
    }

    @ViewBuilder
    private var emptyState: some View {
        if let q = model.searchQuery {
            ContentUnavailableView.search(text: q)
        } else if model.selectedCategory != nil {
            ContentUnavailableView("No articles in this category", systemImage: "tray")
        } else {
            ContentUnavailableView(
                "Nothing saved yet",
                systemImage: "bookmark",
                description: Text("Use Share → Recap in Safari.")
            )
        }
    }

    private func errorRow(_ message: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Label(message, systemImage: "exclamationmark.triangle")
                .font(.footnote)
                .foregroundStyle(Theme.noticeText)
            Spacer()
            Button("Retry") { Task { await model.refresh() } }
                .font(.footnote.weight(.semibold))
                .buttonStyle(.borderless)
        }
        .listRowBackground(Color.clear)
        .listRowSeparator(.hidden)
    }
}
