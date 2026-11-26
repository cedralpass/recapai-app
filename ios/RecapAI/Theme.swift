import SwiftUI

/// Recap brand tokens (design_handoff/ios-README.md).
enum Theme {
    static let tint = Color(hex: 0x3B82F6)          // blue-500
    static let tintDark = Color(hex: 0x1D4ED8)      // blue-700
    static let label = Color(hex: 0x111827)
    static let secondary = Color(hex: 0x6B7280)
    static let tertiary = Color(hex: 0x9CA3AF)
    static let badgeBackground = Color(hex: 0xF3F4F6)
    static let badgeText = Color(hex: 0x374151)
    static let paper = Color(hex: 0xFAFAF9)         // stone-50
    static let ink = Color(hex: 0x0F172A)           // slate-900
    static let amber = Color(hex: 0xD97706)         // amber-600
    static let noticeBackground = Color(hex: 0xFFFBEB)
    static let noticeBorder = Color(hex: 0xFCD34D)
    static let noticeText = Color(hex: 0x92400E)
    static let noticeBody = Color(hex: 0x78350F)
    static let highlight = Color(hex: 0xFEF08A)     // yellow-200
}

extension Color {
    init(hex: UInt32) {
        self.init(
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255
        )
    }
}

/// Grey capsule category badge, same as the web badge.
struct CategoryBadge: View {
    let name: String

    var body: some View {
        Text(name)
            .font(.system(size: 12, weight: .semibold))
            .foregroundStyle(Theme.badgeText)
            .padding(.horizontal, 10)
            .padding(.vertical, 3)
            .background(Theme.badgeBackground, in: Capsule())
            .lineLimit(1)
    }
}

/// Black rounded square with a white "R".
struct BrandMark: View {
    var size: CGFloat = 30

    var body: some View {
        Text("R")
            .font(.system(size: size * 0.53, weight: .heavy))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background(.black, in: RoundedRectangle(cornerRadius: size * 0.26))
            .accessibilityLabel("Recap")
    }
}

/// Amber notice card (summary not available, regenerate banner).
struct NoticeCard<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        content
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.noticeBackground, in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(Theme.noticeBorder))
    }
}

/// Shown on Articles/Digest when no API token is set.
struct ConnectRecapView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        ContentUnavailableView {
            Label("Connect Recap", systemImage: "link")
        } description: {
            Text("Add your server and API token in Settings to see your articles and digest.")
        } actions: {
            Button("Open Settings") { app.selectedTab = .settings }
                .buttonStyle(.borderedProminent)
        }
    }
}

extension Date {
    /// "Nov 24"
    var shortLabel: String { formatted(.dateTime.month(.abbreviated).day()) }
}

/// Highlight literal occurrences of the query's words (3+ letters) in `text`.
func highlighted(_ text: String, query: String) -> AttributedString {
    var result = AttributedString(text)
    let words = query.split(whereSeparator: { $0.isWhitespace }).map(String.init).filter { $0.count >= 3 }
    for word in words {
        var searchStart = result.startIndex
        while searchStart < result.endIndex,
              let range = result[searchStart...].range(of: word, options: [.caseInsensitive, .diacriticInsensitive]) {
            result[range].backgroundColor = Theme.highlight
            searchStart = range.upperBound
        }
    }
    return result
}
