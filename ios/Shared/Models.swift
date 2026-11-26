import Foundation

/// An article as returned by the read API (`GET /api/v1/articles…`).
struct Article: Codable, Identifiable, Hashable, Sendable {
    let id: Int
    let url: String
    let title: String?
    let summary: String?
    let author: String?
    let category: String?
    let keyTopics: [String]
    let source: String?
    let created: Date?
    var read: Bool
    let summaryAvailable: Bool

    var displayTitle: String {
        if let title, !title.isEmpty { return title }
        return source ?? url
    }

    /// Author to show, hiding the placeholders the classifier writes when it can't tell.
    var displayAuthor: String? {
        guard let author, !author.isEmpty else { return nil }
        let placeholders = ["unknown", "not specified", "n/a", "none"]
        return placeholders.contains(author.lowercased()) ? nil : author
    }

    var webURL: URL? { URL(string: url) }
}

struct ArticlePage: Codable, Sendable {
    let articles: [Article]
    let page: Int
    let hasNext: Bool
}

struct SearchResults: Codable, Sendable {
    let articles: [Article]
    let query: String
}

struct CategoryCount: Codable, Hashable, Sendable, Identifiable {
    let name: String
    let count: Int
    var id: String { name }
}

struct CategoryList: Codable, Sendable {
    let categories: [CategoryCount]
}

struct Digest: Codable, Identifiable, Sendable {
    let id: Int
    let weekStart: String?
    let articleCount: Int?
    let clusterCount: Int?
    let digestHtml: String?
    let bookmarksSince: Int
    let showRegenerate: Bool
    let wasUnread: Bool

    /// "November 17" from the ISO date "2026-11-17".
    var weekStartLabel: String? {
        guard let weekStart else { return nil }
        let parser = DateFormatter()
        parser.locale = Locale(identifier: "en_US_POSIX")
        parser.dateFormat = "yyyy-MM-dd"
        parser.timeZone = TimeZone(identifier: "UTC")
        guard let date = parser.date(from: weekStart) else { return nil }
        let out = DateFormatter()
        out.setLocalizedDateFormatFromTemplate("MMMMd")
        out.timeZone = TimeZone(identifier: "UTC")
        return out.string(from: date)
    }
}

/// `GET /api/v1/digest/latest`: either a digest or none yet (404 with a count for the empty state).
enum DigestLatest: Sendable {
    case digest(Digest)
    case none(articlesSinceLast: Int)
}

struct JobStatus: Codable, Sendable {
    let status: String

    var isFinished: Bool { status == "finished" }
    var isFailed: Bool { ["failed", "stopped", "canceled", "not_found"].contains(status) }
}

struct QueuedJob: Codable, Sendable {
    let status: String
    let jobId: String
}
