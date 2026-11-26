import SwiftUI

struct SettingsView: View {
    @Environment(AppModel.self) private var app
    @State private var serverURL = RecapSettings.serverURL
    @State private var apiToken = RecapSettings.apiToken
    @State private var showToken = false
    @State private var savedMessage: String?
    @State private var lastSaveAt = RecapSettings.lastSaveAt

    private var isDirty: Bool {
        serverURL.trimmingCharacters(in: .whitespaces) != RecapSettings.serverURL
            || apiToken.trimmingCharacters(in: .whitespacesAndNewlines) != RecapSettings.apiToken
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Server").font(.footnote).foregroundStyle(.secondary)
                        TextField("https://dev.recaprai.com", text: $serverURL)
                            .keyboardType(.URL)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    }
                    VStack(alignment: .leading, spacing: 2) {
                        Text("API token").font(.footnote).foregroundStyle(.secondary)
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
                    }
                    if isDirty || savedMessage != nil {
                        Button("Save") { save() }
                            .disabled(!isDirty || serverURL.isEmpty || apiToken.isEmpty)
                        if let savedMessage, !isDirty {
                            Text(savedMessage).font(.footnote).foregroundStyle(.secondary)
                        }
                    }
                } header: {
                    Text("Account")
                } footer: {
                    Text("Find your token in Recap under Settings → API Token.")
                }

                Section("Share extension") {
                    connectionRow
                    NavigationLink("How to add Recap to the share sheet") { ShareSheetHelpView() }
                        .foregroundStyle(Theme.tint)
                }

                Section("More") {
                    if let webURL = URL(string: RecapSettings.serverURL), webURL.scheme != nil {
                        Link(destination: webURL) {
                            HStack {
                                Text("Open Recap on the web").foregroundStyle(Theme.label)
                                Spacer()
                                Image(systemName: "arrow.up.right").foregroundStyle(Theme.tertiary)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Settings")
            .onAppear { lastSaveAt = RecapSettings.lastSaveAt }
        }
    }

    @ViewBuilder
    private var connectionRow: some View {
        if !app.isConfigured {
            Label("Not connected — add your token above", systemImage: "exclamationmark.circle.fill")
                .foregroundStyle(Theme.amber)
        } else if let lastSaveAt {
            Label {
                Text("Connected — last save \(lastSaveAt.formatted(.relative(presentation: .named)))")
            } icon: {
                Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
            }
        } else {
            Label {
                Text("Connected — no saves from Safari yet")
            } icon: {
                Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
            }
        }
    }

    private func save() {
        RecapSettings.serverURL = serverURL.trimmingCharacters(in: .whitespaces)
        RecapSettings.apiToken = apiToken.trimmingCharacters(in: .whitespacesAndNewlines)
        serverURL = RecapSettings.serverURL
        apiToken = RecapSettings.apiToken
        savedMessage = "Saved. You can now share from Safari."
        app.settingsChanged()
    }
}

struct ShareSheetHelpView: View {
    var body: some View {
        List {
            Section("Save an article") {
                Label("Open an article in Safari", systemImage: "safari")
                Label("Tap the Share button", systemImage: "square.and.arrow.up")
                Label("Choose Recap", systemImage: "bookmark")
            }
            Section {
                Label("Scroll the app row to the end and tap More", systemImage: "ellipsis.circle")
                Label("Tap Edit, then add Recap to Favorites", systemImage: "star")
                Label("Drag it up so it's always one tap away", systemImage: "line.3.horizontal")
            } header: {
                Text("Don't see Recap?")
            } footer: {
                Text("Recap sends the page as you see it, so sites that block Recap still get summarized.")
            }
        }
        .navigationTitle("Share sheet")
        .navigationBarTitleDisplayMode(.inline)
    }
}
