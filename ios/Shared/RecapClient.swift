import Foundation

/// Settings shared between the app and the share extension via the App Group.
enum RecapSettings {
    static let appGroup = "group.com.gsmalling.recapai"
    static let defaultServerURL = "https://dev.recaprai.com"

    private static var store: UserDefaults {
        UserDefaults(suiteName: appGroup) ?? .standard
    }

    static var serverURL: String {
        get { store.string(forKey: "serverURL") ?? defaultServerURL }
        set { store.set(newValue, forKey: "serverURL") }
    }

    static var apiToken: String {
        get { store.string(forKey: "apiToken") ?? "" }
        set { store.set(newValue, forKey: "apiToken") }
    }

    /// When the share extension last saved an article (shown in Settings).
    static var lastSaveAt: Date? {
        get { store.object(forKey: "lastSaveAt") as? Date }
        set { store.set(newValue, forKey: "lastSaveAt") }
    }

    static var isConfigured: Bool {
        !serverURL.isEmpty && !apiToken.isEmpty
    }
}

/// Outcome of POST /api/v1/articles, mirroring the Chrome extension's messages.
enum SaveResult: Sendable {
    case queued
    case updated
    case exists

    var message: String {
        switch self {
        case .queued: "Saved! Recap is summarizing it."
        case .updated: "Updated with full text — re-summarizing."
        case .exists: "Already in your Recap list."
        }
    }
}

enum RecapError: LocalizedError {
    case notConfigured
    case badServerURL
    case unauthorized
    case server(String)
    case network
    case notFound

    var errorDescription: String? {
        switch self {
        case .notConfigured: "Open the Recap app and add your API token first."
        case .badServerURL: "The server URL in the Recap app isn't valid."
        case .unauthorized: "Invalid API token. Update it in the Recap app."
        case .server(let message): message
        case .network: "Couldn't reach Recap. Check your connection or server URL."
        case .notFound: "That item isn't in your Recap list any more."
        }
    }
}

struct RecapClient: Sendable {
    /// The server rejects bodies over 5 MB; leave headroom for the JSON wrapper.
    static let maxHTMLBytes = 4_500_000

    let serverURL: String
    let apiToken: String

    init(serverURL: String = RecapSettings.serverURL, apiToken: String = RecapSettings.apiToken) {
        self.serverURL = serverURL
        self.apiToken = apiToken
    }

    func saveArticle(url: String, html: String?) async throws -> SaveResult {
        guard !apiToken.isEmpty else { throw RecapError.notConfigured }
        let base = serverURL.trimmingCharacters(in: .whitespaces).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard let endpoint = URL(string: base + "/api/v1/articles") else { throw RecapError.badServerURL }

        var body: [String: String] = ["url": url]
        if let html, html.utf8.count <= Self.maxHTMLBytes {
            body["html"] = html
        }

        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.timeoutInterval = 30
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("ios-share/\(Self.appVersion)", forHTTPHeaderField: "X-Recap-Client")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw RecapError.network
        }
        guard let http = response as? HTTPURLResponse else { throw RecapError.network }

        let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        switch http.statusCode {
        case 201:
            RecapSettings.lastSaveAt = Date()
            return .queued
        case 200:
            RecapSettings.lastSaveAt = Date()
            return json?["status"] as? String == "updated" ? .updated : .exists
        case 401:
            throw RecapError.unauthorized
        default:
            throw RecapError.server(json?["error"] as? String ?? "Server error (\(http.statusCode))")
        }
    }

    // MARK: - Read API (iOS app)

    func listArticles(page: Int = 1, perPage: Int = 20, category: String? = nil) async throws -> ArticlePage {
        var query = [URLQueryItem(name: "page", value: String(page)), URLQueryItem(name: "per_page", value: String(perPage))]
        if let category { query.append(URLQueryItem(name: "category", value: category)) }
        return try await decode(ArticlePage.self, from: send("GET", "/api/v1/articles", query: query))
    }

    func searchArticles(_ q: String, category: String? = nil) async throws -> [Article] {
        var query = [URLQueryItem(name: "q", value: q)]
        if let category { query.append(URLQueryItem(name: "category", value: category)) }
        return try await decode(SearchResults.self, from: send("GET", "/api/v1/articles/search", query: query)).articles
    }

    func article(id: Int) async throws -> Article {
        try await decode(Article.self, from: send("GET", "/api/v1/articles/\(id)"))
    }

    func setRead(_ read: Bool, articleID: Int) async throws -> Article {
        let body = try JSONSerialization.data(withJSONObject: ["read": read])
        return try await decode(Article.self, from: send("POST", "/api/v1/articles/\(articleID)/read", body: body))
    }

    func deleteArticle(id: Int) async throws {
        _ = try await send("DELETE", "/api/v1/articles/\(id)")
    }

    func categories() async throws -> [CategoryCount] {
        try await decode(CategoryList.self, from: send("GET", "/api/v1/categories")).categories
    }

    /// Latest completed digest. `markOpened: false` peeks without clearing the unread state.
    func latestDigest(markOpened: Bool = true) async throws -> DigestLatest {
        let query = markOpened ? [] : [URLQueryItem(name: "mark_opened", value: "false")]
        let (data, status) = try await send("GET", "/api/v1/digest/latest", query: query, allow404: true)
        if status == 404 {
            let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            return .none(articlesSinceLast: json?["articles_since_last"] as? Int ?? 0)
        }
        return .digest(try decode(Digest.self, from: (data, status)))
    }

    func generateDigest() async throws -> String {
        try await decode(QueuedJob.self, from: send("POST", "/api/v1/digest/generate")).jobId
    }

    func digestJobStatus(_ jobID: String) async throws -> JobStatus {
        let (data, status) = try await send("GET", "/api/v1/digest/job/\(jobID)", allow404: true)
        if status == 404 { return JobStatus(status: "not_found") }
        return try decode(JobStatus.self, from: (data, status))
    }

    private static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    private func decode<T: Decodable>(_ type: T.Type, from response: (Data, Int)) throws -> T {
        do {
            return try Self.decoder.decode(type, from: response.0)
        } catch {
            throw RecapError.server("Unexpected response from Recap.")
        }
    }

    /// Authenticated request; returns body + status, mapping 401/404/errors to RecapError.
    private func send(
        _ method: String,
        _ path: String,
        query: [URLQueryItem] = [],
        body: Data? = nil,
        allow404: Bool = false
    ) async throws -> (Data, Int) {
        guard !apiToken.isEmpty else { throw RecapError.notConfigured }
        let base = serverURL.trimmingCharacters(in: .whitespaces).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard var components = URLComponents(string: base + path) else { throw RecapError.badServerURL }
        if !query.isEmpty { components.queryItems = query }
        guard let endpoint = components.url, endpoint.scheme != nil else { throw RecapError.badServerURL }

        var request = URLRequest(url: endpoint)
        request.httpMethod = method
        request.timeoutInterval = 30
        request.setValue("Bearer \(apiToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: request)
        } catch {
            throw RecapError.network
        }
        guard let http = response as? HTTPURLResponse else { throw RecapError.network }
        switch http.statusCode {
        case 200..<300:
            return (data, http.statusCode)
        case 401:
            throw RecapError.unauthorized
        case 404 where allow404:
            return (data, 404)
        case 404:
            throw RecapError.notFound
        default:
            let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
            throw RecapError.server(json?["error"] as? String ?? "Server error (\(http.statusCode))")
        }
    }

    private static var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    }
}
