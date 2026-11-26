import SwiftUI

@main
struct RecapAIApp: App {
    var body: some Scene {
        WindowGroup {
            SettingsView()
        }
    }
}

struct SettingsView: View {
    @State private var serverURL = RecapSettings.serverURL
    @State private var apiToken = RecapSettings.apiToken
    @State private var showToken = false
    @State private var status: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("https://dev.recaprai.com", text: $serverURL)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                } header: {
                    Text("Server URL")
                }

                Section {
                    HStack {
                        Group {
                            if showToken {
                                TextField("Paste your API token", text: $apiToken)
                            } else {
                                SecureField("Paste your API token", text: $apiToken)
                            }
                        }
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        Button(showToken ? "Hide" : "Show") { showToken.toggle() }
                            .buttonStyle(.borderless)
                    }
                } header: {
                    Text("API Token")
                } footer: {
                    Text("Find your token in Recap under Settings → API Token.")
                }

                Section {
                    Button("Save") { save() }
                        .frame(maxWidth: .infinity)
                        .disabled(serverURL.isEmpty || apiToken.isEmpty)
                    if let status {
                        Text(status).foregroundStyle(.secondary)
                    }
                }

                Section("How to save articles") {
                    Label("Open an article in Safari", systemImage: "safari")
                    Label("Tap the Share button", systemImage: "square.and.arrow.up")
                    Label("Choose Recap", systemImage: "bookmark")
                }
            }
            .navigationTitle("Recap")
        }
    }

    private func save() {
        RecapSettings.serverURL = serverURL.trimmingCharacters(in: .whitespaces)
        RecapSettings.apiToken = apiToken.trimmingCharacters(in: .whitespacesAndNewlines)
        status = "Saved. You can now share from Safari."
    }
}
