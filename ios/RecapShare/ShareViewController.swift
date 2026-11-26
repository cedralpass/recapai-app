import SwiftUI
import UIKit
import UniformTypeIdentifiers

/// Share extension entry point. Pulls the page URL/title/HTML from Safari
/// (via GetPage.js) and posts it to Recap straight away.
final class ShareViewController: UIViewController {
    private let model = ShareModel()

    override func viewDidLoad() {
        super.viewDidLoad()
        model.onDone = { [weak self] in
            self?.extensionContext?.completeRequest(returningItems: nil)
        }

        let host = UIHostingController(rootView: ShareView(model: model))
        addChild(host)
        host.view.translatesAutoresizingMaskIntoConstraints = false
        host.view.backgroundColor = .clear
        view.addSubview(host.view)
        NSLayoutConstraint.activate([
            host.view.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            host.view.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            host.view.topAnchor.constraint(equalTo: view.topAnchor),
            host.view.bottomAnchor.constraint(equalTo: view.bottomAnchor),
        ])
        host.didMove(toParent: self)

        let items = (extensionContext?.inputItems as? [NSExtensionItem]) ?? []
        Task { await model.run(items: items) }
    }
}

struct SharedPage: Sendable {
    var url: String
    var title: String?
    var html: String?
}

@MainActor
@Observable
final class ShareModel {
    enum Phase {
        case loading
        case saving
        case success(String)
        case failure(String)
    }

    var phase: Phase = .loading
    var page: SharedPage?
    var onDone: () -> Void = {}

    func run(items: [NSExtensionItem]) async {
        guard RecapSettings.isConfigured else {
            phase = .failure(RecapError.notConfigured.localizedDescription)
            return
        }
        guard let page = await Self.extractPage(from: items) else {
            phase = .failure("Couldn't find a web page to save.")
            return
        }
        self.page = page
        phase = .saving
        do {
            let result = try await RecapClient().saveArticle(url: page.url, html: page.html)
            phase = .success(result.message)
            try? await Task.sleep(for: .seconds(1.5))
            onDone()
        } catch {
            phase = .failure(error.localizedDescription)
        }
    }

    /// Prefer Safari's JS preprocessing results (URL + rendered HTML); fall back to a plain URL.
    private static func extractPage(from items: [NSExtensionItem]) async -> SharedPage? {
        let providers = items.flatMap { $0.attachments ?? [] }

        for provider in providers where provider.hasItemConformingToTypeIdentifier(UTType.propertyList.identifier) {
            if let dict = try? await provider.loadItem(forTypeIdentifier: UTType.propertyList.identifier) as? NSDictionary,
               let results = dict[NSExtensionJavaScriptPreprocessingResultsKey] as? [String: Any],
               let url = results["url"] as? String {
                return SharedPage(url: url, title: results["title"] as? String, html: results["html"] as? String)
            }
        }

        for provider in providers where provider.hasItemConformingToTypeIdentifier(UTType.url.identifier) {
            if let url = try? await provider.loadItem(forTypeIdentifier: UTType.url.identifier) as? URL {
                return SharedPage(url: url.absoluteString)
            }
        }
        return nil
    }
}

struct ShareView: View {
    let model: ShareModel

    var body: some View {
        VStack(spacing: 16) {
            HStack {
                Text("Recap").font(.headline)
                Spacer()
                Button("Done") { model.onDone() }
            }

            if let page = model.page {
                VStack(alignment: .leading, spacing: 4) {
                    Text(page.title?.isEmpty == false ? page.title! : page.url)
                        .font(.subheadline.weight(.semibold))
                        .lineLimit(2)
                    Text(page.url)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }

            Group {
                switch model.phase {
                case .loading, .saving:
                    HStack(spacing: 8) {
                        ProgressView()
                        Text("Saving to Recap…")
                    }
                case .success(let message):
                    Label(message, systemImage: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                case .failure(let message):
                    Label(message, systemImage: "exclamationmark.triangle.fill")
                        .foregroundStyle(.red)
                }
            }
            .font(.callout)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(20)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20))
        .padding()
        .frame(maxHeight: .infinity, alignment: .center)
    }
}
