import SwiftUI
import WebKit

/// Renders the server's `digest_html` (the email template) inside the native digest card.
/// Sizes itself to its content so it can sit in a ScrollView; taps on links go to `onLink`.
struct DigestWebView: UIViewRepresentable {
    let html: String
    @Binding var height: CGFloat
    let onLink: (URL) -> Void

    /// The native card already shows the eyebrow/title/counts, so hide the email masthead and
    /// strip the email's outer padding/background. Body sans, headings serif, tint links.
    private static let injectedCSS = """
    html, body { margin: 0 !important; padding: 0 !important; background: transparent !important;
      -webkit-text-size-adjust: 100%; }
    body { font-family: -apple-system, system-ui, sans-serif !important; }
    table { background: transparent !important; }
    .container { padding: 0 !important; }
    table[width="600"] { width: 100% !important; max-width: 100% !important; box-shadow: none !important; }
    .card-pad-head { display: none !important; }
    .card-pad-body { padding: 0 0 4px !important; }
    .card-pad-foot { padding: 16px 0 8px !important; }
    .narrative { font-family: -apple-system, system-ui, sans-serif !important; font-size: 15px !important;
      line-height: 1.5 !important; color: #334155 !important; }
    .cluster-label { font-family: "New York", ui-serif, Georgia, serif !important; text-transform: none !important;
      letter-spacing: 0 !important; font-size: 19px !important; color: #0f172a !important; }
    h1, h2, h3 { font-family: "New York", ui-serif, Georgia, serif !important; }
    a { color: #1d4ed8 !important; }
    .article-link span { display: none !important; }  /* the ↗ glyph; links open in-app here */
    """

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.dataDetectorTypes = []
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.scrollView.isScrollEnabled = false
        webView.scrollView.bounces = false
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.backgroundColor = .clear
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        context.coordinator.parent = self
        guard context.coordinator.loadedHTML != html else { return }
        context.coordinator.loadedHTML = html
        webView.loadHTMLString(Self.document(for: html), baseURL: nil)
    }

    private static func document(for html: String) -> String {
        let style = "<style>\(injectedCSS)</style>"
        if let range = html.range(of: "</head>", options: .caseInsensitive) {
            return html.replacingCharacters(in: range, with: style + "</head>")
        }
        return """
        <!doctype html><html><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">\(style)</head>
        <body>\(html)</body></html>
        """
    }

    @MainActor
    final class Coordinator: NSObject, WKNavigationDelegate {
        var parent: DigestWebView
        var loadedHTML: String?

        init(_ parent: DigestWebView) { self.parent = parent }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            webView.evaluateJavaScript("document.documentElement.scrollHeight") { [weak self] result, _ in
                guard let self, let value = result as? Double else { return }
                MainActor.assumeIsolated {
                    self.parent.height = CGFloat(value)
                }
            }
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping @MainActor (WKNavigationActionPolicy) -> Void
        ) {
            if navigationAction.navigationType == .linkActivated, let url = navigationAction.request.url {
                parent.onLink(url)
                decisionHandler(.cancel)
                return
            }
            decisionHandler(.allow)
        }
    }
}
