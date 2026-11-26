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

    var errorDescription: String? {
        switch self {
        case .notConfigured: "Open the Recap app and add your API token first."
        case .badServerURL: "The server URL in the Recap app isn't valid."
        case .unauthorized: "Invalid API token. Update it in the Recap app."
        case .server(let message): message
        case .network: "Couldn't reach Recap. Check your connection or server URL."
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
            return .queued
        case 200:
            return json?["status"] as? String == "updated" ? .updated : .exists
        case 401:
            throw RecapError.unauthorized
        default:
            throw RecapError.server(json?["error"] as? String ?? "Server error (\(http.statusCode))")
        }
    }

    private static var appVersion: String {
        Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
    }
}
