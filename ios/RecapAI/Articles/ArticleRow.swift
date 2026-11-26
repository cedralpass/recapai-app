import SwiftUI

/// Article card: title + date, summary (or URL-only notice), category badge + source.
struct ArticleRow: View {
    let article: Article
    var query: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 10) {
                Text(highlighted(article.displayTitle, query: query))
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(article.read ? Theme.badgeText.opacity(0.85) : Theme.label)
                    .lineLimit(2)
                    .frame(maxWidth: .infinity, alignment: .leading)
                if let created = article.created {
                    Text(created.shortLabel)
                        .font(.system(size: 13))
                        .foregroundStyle(Theme.tertiary)
                }
            }

            if article.summaryAvailable, let summary = article.summary {
                Text(highlighted(summary, query: query))
                    .font(.system(size: 14))
                    .foregroundStyle(Color(hex: 0x4B5563))
                    .lineLimit(2)
                    .lineSpacing(2)
            } else {
                Label("Summary not available — tap to read", systemImage: "exclamationmark.triangle")
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.noticeText)
            }

            HStack {
                if let category = article.category {
                    CategoryBadge(name: category)
                }
                Spacer()
                if let source = article.source {
                    Text(source)
                        .font(.system(size: 12))
                        .foregroundStyle(Theme.tertiary)
                        .lineLimit(1)
                }
            }
            .padding(.top, 4)
        }
        .padding(.vertical, 14)
        .padding(.horizontal, 16)
        .background(.white, in: RoundedRectangle(cornerRadius: 14))
        .overlay(alignment: .topLeading) {
            if !article.read {
                Circle()
                    .fill(Theme.tint)
                    .frame(width: 7, height: 7)
                    .offset(x: 5, y: 20)
                    .accessibilityLabel("Unread")
            }
        }
        .contentShape(RoundedRectangle(cornerRadius: 14))
    }
}
