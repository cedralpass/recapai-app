import SafariServices
import SwiftUI

/// In-app Safari view for reading the original article.
struct SafariView: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        let controller = SFSafariViewController(url: url)
        controller.preferredControlTintColor = UIColor(Theme.tint)
        return controller
    }

    func updateUIViewController(_ controller: SFSafariViewController, context: Context) {}
}

/// Identifiable wrapper so a URL can drive `.fullScreenCover(item:)`.
struct SafariDestination: Identifiable, Hashable {
    let url: URL
    var id: String { url.absoluteString }
}

extension View {
    func safariCover(_ destination: Binding<SafariDestination?>) -> some View {
        fullScreenCover(item: destination) { destination in
            SafariView(url: destination.url).ignoresSafeArea()
        }
    }
}

/// SFSafariViewController only opens http(s).
func safariURL(_ url: URL?) -> URL? {
    guard let url, let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else { return nil }
    return url
}
